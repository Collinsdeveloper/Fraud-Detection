from datetime import datetime

from flask_restful import Resource, request

from app import db
from ..models.models import AccountEvent
from ..schemas.schemas import AccountEventSchema
from ..services.alerting import raise_alert
from ..services.risk_engine import evaluate, LEVEL_SUSPICIOUS, LEVEL_FLAGGED
from ..utils.auth import staff_identity
from ..utils.helpers import normalize_msisdn, paginate

ALLOWED_EVENT_TYPES = [
    'LOGIN', 'LOGIN_OTP', 'OTP_REQUEST', 'PIN_CHANGE', 'PASSWORD_RESET',
    'PROFILE_CHANGE', 'NEW_DEVICE', 'BENEFICIARY_CHANGE',
]


def ingest_account(payload):
    """Persist + score account activity for ATO detection. Returns (dict, status)."""
    msisdn = payload.get('msisdn')
    if not msisdn:
        return {'message': 'msisdn is required'}, 400
    msisdn = normalize_msisdn(msisdn)

    event_type = (payload.get('event_type') or '').upper()
    if event_type not in ALLOWED_EVENT_TYPES:
        return {'message': f'event_type must be one of {ALLOWED_EVENT_TYPES}'}, 400

    try:
        dt = datetime.fromisoformat(payload['event_datetime']) if payload.get('event_datetime') else datetime.utcnow()
    except ValueError:
        return {'message': 'event_datetime must be ISO-8601'}, 400
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None)

    event = AccountEvent(
        msisdn=msisdn,
        event_type=event_type,
        device_hash=payload.get('device_hash'),
        ip_address=payload.get('ip_address'),
        location=payload.get('location'),
        details=payload.get('details'),
        event_datetime=dt,
        status='open',
    )
    db.session.add(event)
    db.session.flush()

    verdict = evaluate('ACCOUNT', event)
    event.risk_score = verdict['score']
    event.risk_level = verdict['level']
    event.reasons = verdict['reasons']
    db.session.add(event)
    db.session.flush()

    alert = None
    if verdict['level'] in (LEVEL_SUSPICIOUS, LEVEL_FLAGGED):
        flag = verdict['level'] == LEVEL_FLAGGED
        title = ('Account takeover FLAGGED' if flag else 'Suspicious account activity')
        message = (
            f'{event_type.replace("_", " ").title()} on {msisdn} at '
            f'{dt.strftime("%d %b %Y %H:%M")} '
            + (' '.join(verdict['reasons'][:3]))
        )
        alert = raise_alert(
            'ACCOUNT_TAKEOVER', msisdn, title, message,
            verdict['score'], verdict['level'],
            flag_subscriber=flag,
            flag_reason='ACCOUNT TAKEOVER PATTERN DETECTED',
        )
    db.session.commit()

    response = AccountEventSchema.dump(event)
    if alert:
        response['alert'] = {
            'alert_id': alert.alert_id,
            'severity': alert.severity,
            'status': alert.status,
            'channel_sent': alert.channel_sent,
            'title': alert.title,
        }
    return response, 201


class AccountEventList(Resource):
    """GET/POST /account/events --- POST ingests account activity for ATO scoring."""

    def get(self, event_id=0):
        identity, error = staff_identity()
        if error:
            return error
        if event_id:
            event = AccountEvent.query.get(event_id)
            if not event:
                return {'message': 'Account event not found'}, 404
            return AccountEventSchema.dump(event), 200

        query = AccountEvent.query
        if request.args.get('risk_level'):
            query = query.filter(AccountEvent.risk_level == request.args['risk_level'].lower())
        if request.args.get('event_type'):
            query = query.filter(AccountEvent.event_type == request.args['event_type'].upper())
        msisdn = request.args.get('msisdn')
        if msisdn:
            query = query.filter(AccountEvent.msisdn == normalize_msisdn(msisdn))
        query = query.order_by(AccountEvent.event_datetime.desc())
        return paginate(query, AccountEventSchema.dump), 200

    def post(self):
        identity, error = staff_identity()
        if error:
            return error
        payload = request.get_json(force=True) or {}
        return ingest_account(payload)


class AccountEventDetail(Resource):
    """GET /account/events/<int:event_id>"""

    def get(self, event_id):
        identity, error = staff_identity()
        if error:
            return error
        event = AccountEvent.query.get(event_id)
        if not event:
            return {'message': 'Account event not found'}, 404
        return AccountEventSchema.dump(event), 200
