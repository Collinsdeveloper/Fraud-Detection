"""Africa's Talking USSD callback for subscriber self-service fraud tools.

USSD is session based: the telco POSTs the accumulated input to the callback URL
registered on the USSD channel and expects a plain-text reply:

    CON <text>   -> keep the session open (show the next screen)
    END <text>   -> close the session

Design notes:
  * No JWT. Africa's Talking cannot send an Authorization header, so this route
    is intentionally public. It only ever exposes data for the calling number.
  * Keep the handler fast (USSD sessions time out around 20-30s), so no
    outbound SMS/Voice calls are made from inside the session.
  * `text` is the full path the subscriber has dialled: '' -> '1' -> '1*2'.
"""
from flask import Response, current_app, request
from flask_restful import Resource

from app import db
from ..models.models import Alert, Subscriber
from ..utils.helpers import normalize_msisdn

CON = 'CON '
END = 'END '

MENU = (
    'FraudShield\n'
    '1. Check my line status\n'
    '2. Report suspicious SIM swap\n'
    '3. Alert settings\n'
    '4. Fraud help desk'
)

CHANNEL_CHOICES = {
    '1': ('sms', 'SMS'),
    '2': ('voice', 'Voice call'),
    '3': ('both', 'SMS + Voice'),
    '4': ('none', 'No alerts'),
}


def _reply(body):
    """USSD replies must be plain text; CON keeps the session, END closes it."""
    return Response(body, mimetype='text/plain')


def _params():
    """Read the callback payload from form, JSON or query string."""
    data = {}
    if request.method == 'POST':
        data.update(request.form.to_dict())
        if not data:
            data.update(request.get_json(silent=True) or {})
    data.update(request.args.to_dict())
    return data


def _subscriber_for(msisdn):
    """Return the subscriber for this line, registering it on first contact."""
    subscriber = Subscriber.query.filter_by(msisdn=msisdn).first()
    if subscriber is None:
        subscriber = Subscriber(msisdn=msisdn, alert_channel='sms', status='active')
        db.session.add(subscriber)
        db.session.commit()
        current_app.logger.info('USSD auto-registered subscriber %s', msisdn)
    return subscriber


def _line_status(subscriber):
    open_alerts = Alert.query.filter_by(
        msisdn=subscriber.msisdn, status='open'
    ).count()
    return END + (
        f'Line {subscriber.msisdn}\n'
        f'Status: {subscriber.status.upper()}\n'
        f'Alerts: {open_alerts} open\n'
        f'Alert channel: {subscriber.alert_channel.upper()}\n'
        f'Dial 4 for the fraud desk.'
    )


def _report_confirm(subscriber):
    """Flag the line and raise an alert for the analyst queue (no SMS here)."""
    if subscriber.status == 'active':
        subscriber.status = 'flagged'
        subscriber.flagged_reason = 'Subscriber reported a suspicious SIM swap via USSD'
    db.session.add(Alert(
        alert_type='SIM_SWAP',
        msisdn=subscriber.msisdn,
        title='Subscriber-reported SIM swap concern',
        message=(
            f'{subscriber.msisdn} reported a suspected SIM swap / fraud attempt '
            'through the USSD menu.'
        ),
        severity='HIGH',
        risk_score=70,
        status='open',
        channel_sent='NONE',
    ))
    db.session.add(subscriber)
    db.session.commit()
    return (
        'Thanks. Your line is now on the fraud watch list and an analyst has '
        'been alerted. Contact the fraud desk if money has moved.'
    )


class UssdCallback(Resource):
    """GET/POST /ussd — the callback URL registered on the USSD channel."""

    def post(self):
        return self._handle()

    def get(self):
        return self._handle()

    def _handle(self):
        data = _params()
        raw_msisdn = (data.get('phoneNumber') or '').strip()
        text = (data.get('text') or '').strip()
        session_id = data.get('sessionId') or '-'

        if not raw_msisdn:
            return _reply(END + 'We could not read your phone number. Please try again.')

        msisdn = normalize_msisdn(raw_msisdn)
        subscriber = _subscriber_for(msisdn)
        steps = [step for step in text.split('*') if step] if text else []
        current_app.logger.info(
            'USSD %s %s service=%s text=%r',
            session_id, msisdn, data.get('serviceCode') or '-', text,
        )
        return _reply(self._route(subscriber, steps))

    def _route(self, subscriber, steps):
        """Map the dialled path to a CON/END reply."""
        if not steps:
            return CON + MENU

        choice = steps[0]

        if choice == '1':
            return _line_status(subscriber)

        if choice == '2':
            if len(steps) == 1:
                return CON + 'Report a suspicious SIM swap on this line?\n1. Yes\n2. Cancel'
            if steps[1] == '1':
                return END + _report_confirm(subscriber)
            return END + 'Cancelled. No changes were made.'

        if choice == '3':
            if len(steps) == 1:
                return CON + (
                    'Alert settings\n'
                    '1. SMS\n2. Voice call\n3. SMS + Voice\n4. No alerts'
                )
            picked = CHANNEL_CHOICES.get(steps[1])
            if not picked:
                return END + 'Invalid option. Dial again to change your alert settings.'
            subscriber.alert_channel = picked[0]
            db.session.add(subscriber)
            db.session.commit()
            return END + f'Alert channel set to {picked[1]}.'

        if choice == '4':
            return END + (
                'Fraud help desk: call your service provider on 100 and quote '
                'FraudShield. If money moved, report to your bank immediately.'
            )

        return END + 'Invalid option. Please dial again.'
