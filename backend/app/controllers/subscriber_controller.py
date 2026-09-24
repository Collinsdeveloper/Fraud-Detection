from flask_restful import Resource, request

from app import db
from ..models.models import Subscriber
from ..schemas.schemas import SubscriberSchema
from ..utils.auth import staff_identity
from ..utils.helpers import normalize_msisdn, paginate


def _subscriber_body(data, msisdn_default=None):
    """Build a Subscriber from request JSON, normalizing the MSISDN."""
    first = (data.get('first_name') or '').strip()
    last = (data.get('last_name') or '').strip()
    msisdn = data.get('msisdn') or msisdn_default
    if not msisdn:
        return None, {'message': 'msisdn is required'}, 400
    msisdn = normalize_msisdn(msisdn)

    subscriber = Subscriber(
        msisdn=msisdn,
        first_name=first or None,
        last_name=last or None,
        network=(data.get('network') or 'SAFARICOM').upper(),
        is_vip=bool(data.get('is_vip', False)),
        alert_channel=(data.get('alert_channel') or 'sms').lower(),
        status=(data.get('status') or 'active').lower(),
        flagged_reason=data.get('flagged_reason'),
    )
    return subscriber, None, None


class SubscriberList(Resource):
    """GET/POST /subscribers"""

    def get(self, subscriber_id=0):
        identity, error = staff_identity()
        if error:
            return error
        if subscriber_id:
            subscriber = Subscriber.query.get(subscriber_id)
            if not subscriber:
                return {'message': 'Subscriber not found'}, 404
            return SubscriberSchema.dump(subscriber), 200

        query = Subscriber.query
        if request.args.get('status'):
            query = query.filter(Subscriber.status == request.args['status'].lower())
        if request.args.get('network'):
            query = query.filter(Subscriber.network == request.args['network'].upper())
        q = (request.args.get('q') or '').strip()
        if q:
            like = f'%{q}%'
            query = query.filter(
                db.or_(
                    Subscriber.msisdn.like(like),
                    Subscriber.first_name.ilike(like),
                    Subscriber.last_name.ilike(like),
                )
            )
        query = query.order_by(Subscriber.created_at.desc())
        return paginate(query, SubscriberSchema.dump), 200

    def post(self):
        identity, error = staff_identity()
        if error:
            return error
        data = request.get_json(force=True) or {}
        subscriber, err, code = _subscriber_body(data)
        if err:
            return err, code
        if Subscriber.query.filter_by(msisdn=subscriber.msisdn).first():
            return {'message': 'A subscriber with this number already exists'}, 400
        db.session.add(subscriber)
        db.session.commit()
        return SubscriberSchema.dump(subscriber), 201


class SubscriberDetail(Resource):
    """GET/PUT/DELETE /subscribers/<int:subscriber_id>"""

    def get(self, subscriber_id):
        identity, error = staff_identity()
        if error:
            return error
        subscriber = Subscriber.query.get(subscriber_id)
        if not subscriber:
            return {'message': 'Subscriber not found'}, 404
        return SubscriberSchema.dump(subscriber), 200

    def put(self, subscriber_id):
        identity, error = staff_identity()
        if error:
            return error
        subscriber = Subscriber.query.get(subscriber_id)
        if not subscriber:
            return {'message': 'Subscriber not found'}, 404
        data = request.get_json(force=True) or {}

        if data.get('msisdn'):
            subscriber.msisdn = normalize_msisdn(data['msisdn'])
            clash = Subscriber.query.filter(
                Subscriber.msisdn == subscriber.msisdn,
                Subscriber.subscriber_id != subscriber.subscriber_id,
            ).first()
            if clash:
                return {'message': 'Another subscriber already has this number'}, 400
        if 'first_name' in data:
            subscriber.first_name = (data['first_name'] or '').strip() or None
        if 'last_name' in data:
            subscriber.last_name = (data['last_name'] or '').strip() or None
        if data.get('network'):
            subscriber.network = data['network'].upper()
        if 'is_vip' in data:
            subscriber.is_vip = bool(data['is_vip'])
        if data.get('alert_channel'):
            subscriber.alert_channel = data['alert_channel'].lower()
        if data.get('status'):
            subscriber.status = data['status'].lower()
        if 'flagged_reason' in data:
            subscriber.flagged_reason = data['flagged_reason']

        db.session.add(subscriber)
        db.session.commit()
        return SubscriberSchema.dump(subscriber), 200

    def delete(self, subscriber_id):
        identity, error = staff_identity()
        if error:
            return error
        subscriber = Subscriber.query.get(subscriber_id)
        if not subscriber:
            return {'message': 'Subscriber not found'}, 404
        db.session.delete(subscriber)
        db.session.commit()
        return {'message': 'Subscriber deleted'}, 200
