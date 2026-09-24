from datetime import datetime, timedelta

from flask_restful import Resource, request

from app import db
from ..models.models import AirtimeTransferEvent
from ..schemas.schemas import AirtimeTransferEventSchema
from ..services.alerting import raise_alert
from ..services.risk_engine import evaluate, LEVEL_SUSPICIOUS, LEVEL_FLAGGED
from ..utils.auth import staff_identity
from ..utils.helpers import normalize_msisdn, paginate


def ingest_airtime(payload):
    """Persist + score an airtime transfer. Returns (response_dict, status_code)."""
    sender = payload.get('sender_msisdn')
    recipient = payload.get('recipient_msisdn')
    amount = payload.get('amount')
    if not sender or not recipient or amount is None:
        return {'message': 'sender_msisdn, recipient_msisdn and amount are required'}, 400
    sender, recipient = normalize_msisdn(sender), normalize_msisdn(recipient)
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return {'message': 'amount must be a number'}, 400

    try:
        dt = datetime.fromisoformat(payload['transfer_datetime']) if payload.get('transfer_datetime') else datetime.utcnow()
    except ValueError:
        return {'message': 'transfer_datetime must be ISO-8601'}, 400
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None)

    # First-time recipient? Compares against existing transfer history.
    prev = AirtimeTransferEvent.query.filter(
        AirtimeTransferEvent.sender_msisdn == sender,
        AirtimeTransferEvent.recipient_msisdn == recipient,
    ).first()
    if 'is_new_recipient' in payload:
        is_new = bool(payload['is_new_recipient'])
    else:
        is_new = prev is None

    # Velocity: transfers made from the sender line in the last 60 minutes
    window_start = dt - timedelta(minutes=60)
    velocity = AirtimeTransferEvent.query.filter(
        AirtimeTransferEvent.sender_msisdn == sender,
        AirtimeTransferEvent.transfer_datetime >= window_start,
        AirtimeTransferEvent.transfer_datetime <= dt,
    ).count()

    event = AirtimeTransferEvent(
        sender_msisdn=sender,
        recipient_msisdn=recipient,
        amount=amount,
        method=(payload.get('method') or '').upper() or None,
        transfer_datetime=dt,
        is_new_recipient=is_new,
        transfers_window_60m=velocity,
        status='open',
    )
    db.session.add(event)
    db.session.flush()

    verdict = evaluate('AIRTIME', event)
    event.risk_score = verdict['score']
    event.risk_level = verdict['level']
    event.reasons = verdict['reasons']
    db.session.add(event)
    db.session.flush()

    alert = None
    if verdict['level'] in (LEVEL_SUSPICIOUS, LEVEL_FLAGGED):
        flag = verdict['level'] == LEVEL_FLAGGED
        title = ('Airtime transfer FLAGGED' if flag else 'Unusual airtime transfer')
        message = (
            f'A transfer of KES {amount:,.0f} from {sender} to {recipient} '
            f'at {dt.strftime("%d %b %Y %H:%M")} was flagged. '
            + (' '.join(verdict['reasons'][:3]))
        )
        alert = raise_alert(
            'AIRTIME_TRANSFER', sender, title, message,
            verdict['score'], verdict['level'],
            flag_subscriber=flag,
            flag_reason='FLAGGED AIRTIME PATTERN',
        )
    db.session.commit()

    response = AirtimeTransferEventSchema.dump(event)
    if alert:
        response['alert'] = {
            'alert_id': alert.alert_id,
            'severity': alert.severity,
            'status': alert.status,
            'channel_sent': alert.channel_sent,
            'title': alert.title,
        }
    return response, 201


class AirtimeList(Resource):
    """GET/POST /airtime/transfers --- POST ingests a transfer and scores it."""

    def get(self, event_id=0):
        identity, error = staff_identity()
        if error:
            return error
        if event_id:
            event = AirtimeTransferEvent.query.get(event_id)
            if not event:
                return {'message': 'Airtime transfer not found'}, 404
            return AirtimeTransferEventSchema.dump(event), 200

        query = AirtimeTransferEvent.query
        if request.args.get('risk_level'):
            query = query.filter(AirtimeTransferEvent.risk_level == request.args['risk_level'].lower())
        sender = request.args.get('sender_msisdn')
        if sender:
            query = query.filter(AirtimeTransferEvent.sender_msisdn == normalize_msisdn(sender))
        query = query.order_by(AirtimeTransferEvent.transfer_datetime.desc())
        return paginate(query, AirtimeTransferEventSchema.dump), 200

    def post(self):
        identity, error = staff_identity()
        if error:
            return error
        payload = request.get_json(force=True) or {}
        return ingest_airtime(payload)


class AirtimeDetail(Resource):
    """GET /airtime/transfers/<int:event_id>"""

    def get(self, event_id):
        identity, error = staff_identity()
        if error:
            return error
        event = AirtimeTransferEvent.query.get(event_id)
        if not event:
            return {'message': 'Airtime transfer not found'}, 404
        return AirtimeTransferEventSchema.dump(event), 200
