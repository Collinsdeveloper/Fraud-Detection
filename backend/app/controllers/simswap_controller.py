from datetime import datetime

from flask_restful import Resource, request

from app import db
from ..models.models import SimSwapEvent, Subscriber
from ..schemas.schemas import SimSwapEventSchema
from ..services.alerting import raise_alert
from ..services.risk_engine import evaluate, LEVEL_SUSPICIOUS, LEVEL_FLAGGED
from ..utils.auth import staff_identity
from ..utils.helpers import normalize_msisdn, paginate


def _network_change(old_imsi, new_imsi):
    """Compare MNC prefix (first 6 digits of the IMSI) to detect network change."""
    if not old_imsi or not new_imsi:
        return False
    prefix = lambda imsi: (''.join(ch for ch in imsi if ch.isdigit()))[:6]
    old_p, new_p = prefix(old_imsi), prefix(new_imsi)
    return bool(old_p and new_p) and old_p != new_p


def ingest_sim_swap(payload):
    """Persist + score a SIM swap event. Returns (response_dict, status_code)."""
    msisdn = payload.get('msisdn')
    if not msisdn:
        return {'message': 'msisdn is required'}, 400
    msisdn = normalize_msisdn(msisdn)

    try:
        swap_datetime = datetime.fromisoformat(payload['swap_datetime']) if payload.get('swap_datetime') else datetime.utcnow()
    except ValueError:
        return {'message': 'swap_datetime must be ISO-8601, e.g. 2026-09-24T10:15:30'}, 400
    if swap_datetime.tzinfo:
        swap_datetime = swap_datetime.replace(tzinfo=None)

    event = SimSwapEvent(
        msisdn=msisdn,
        old_imsi=payload.get('old_imsi'),
        new_imsi=payload.get('new_imsi'),
        old_iccid=payload.get('old_iccid'),
        new_iccid=payload.get('new_iccid'),
        device_model=payload.get('device_model'),
        channel=(payload.get('channel') or '').upper() or None,
        agent_name=payload.get('agent_name'),
        network_change=_network_change(payload.get('old_imsi'), payload.get('new_imsi')),
        swap_datetime=swap_datetime,
        status='open',
    )
    db.session.add(event)
    db.session.flush()  # need event_id for repeat-swap lookup

    verdict = evaluate('SIM_SWAP', event)
    event.risk_score = verdict['score']
    event.risk_level = verdict['level']
    event.reasons = verdict['reasons']
    db.session.add(event)
    db.session.flush()

    alert = None
    subscriber = Subscriber.query.filter_by(msisdn=msisdn).first()
    if verdict['level'] in (LEVEL_SUSPICIOUS, LEVEL_FLAGGED):
        flag = verdict['level'] == LEVEL_FLAGGED
        title = ('SIM swap FLAGGED' if flag else 'Suspicious SIM swap detected')
        message = (
            f'A SIM swap was registered on {event.msisdn} at '
            f'{swap_datetime.strftime("%d %b %Y %H:%M")} '
            f'via {event.channel or "unknown"} channel. '
            + (' '.join(verdict['reasons'][:3]))
        )
        alert = raise_alert(
            'SIM_SWAP', msisdn, title, message,
            verdict['score'], verdict['level'],
            flag_subscriber=flag,
            flag_reason='FLAGGED SIM SWAP: ' + verdict['reasons'][0] if verdict['reasons'] else title,
        )
    elif subscriber and subscriber.status == 'flagged':
        # An active fraud watch cleared by a clean swap
        subscriber.status = 'active'
        subscriber.flagged_reason = None
        db.session.add(subscriber)

    db.session.commit()

    response = SimSwapEventSchema.dump(event)
    if alert:
        response['alert'] = {
            'alert_id': alert.alert_id,
            'severity': alert.severity,
            'status': alert.status,
            'channel_sent': alert.channel_sent,
            'title': alert.title,
        }
    return response, 201


class SimSwapList(Resource):
    """GET/POST /sim-swaps --- POST ingests a swap and runs real-time detection."""

    def get(self, event_id=0):
        identity, error = staff_identity()
        if error:
            return error
        if event_id:
            event = SimSwapEvent.query.get(event_id)
            if not event:
                return {'message': 'SIM swap event not found'}, 404
            return SimSwapEventSchema.dump(event), 200

        query = SimSwapEvent.query
        if request.args.get('risk_level'):
            query = query.filter(SimSwapEvent.risk_level == request.args['risk_level'].lower())
        if request.args.get('channel'):
            query = query.filter(SimSwapEvent.channel.ilike(request.args['channel']))
        msisdn = request.args.get('msisdn')
        if msisdn:
            query = query.filter(SimSwapEvent.msisdn == normalize_msisdn(msisdn))
        query = query.order_by(SimSwapEvent.swap_datetime.desc())
        return paginate(query, SimSwapEventSchema.dump), 200

    def post(self):
        identity, error = staff_identity()
        if error:
            return error
        payload = request.get_json(force=True) or {}
        return ingest_sim_swap(payload)


class SimSwapDetail(Resource):
    """GET /sim-swaps/<int:event_id>"""

    def get(self, event_id):
        identity, error = staff_identity()
        if error:
            return error
        event = SimSwapEvent.query.get(event_id)
        if not event:
            return {'message': 'SIM swap event not found'}, 404
        return SimSwapEventSchema.dump(event), 200

