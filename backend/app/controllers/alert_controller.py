from datetime import datetime

from flask_restful import Resource, request

from app import db
from ..models.models import Alert
from ..schemas.schemas import AlertSchema
from ..utils.auth import staff_identity
from ..utils.helpers import paginate


class AlertList(Resource):
    """GET /alerts (with optional status / severity / type filters)"""

    def get(self, alert_id=0):
        identity, error = staff_identity()
        if error:
            return error
        if alert_id:
            alert = Alert.query.get(alert_id)
            if not alert:
                return {'message': 'Alert not found'}, 404
            return AlertSchema.dump(alert), 200

        query = Alert.query
        if request.args.get('status'):
            query = query.filter(Alert.status == request.args['status'].lower())
        if request.args.get('severity'):
            query = query.filter(Alert.severity == request.args['severity'].upper())
        if request.args.get('alert_type'):
            query = query.filter(Alert.alert_type == request.args['alert_type'].upper())
        msisdn = request.args.get('msisdn')
        if msisdn:
            query = query.filter(Alert.msisdn == msisdn)
        query = query.order_by(Alert.created_at.desc())
        return paginate(query, AlertSchema.dump), 200


class AlertStatus(Resource):
    """PUT /alerts/<int:alert_id>/status"""

    def put(self, alert_id):
        identity, error = staff_identity()
        if error:
            return error
        alert = Alert.query.get(alert_id)
        if not alert:
            return {'message': 'Alert not found'}, 404

        data = request.get_json(force=True) or {}
        new_status = (data.get('status') or '').lower()
        if new_status not in ('open', 'acknowledged', 'resolved'):
            return {'message': 'status must be open, acknowledged or resolved'}, 400

        alert.status = new_status
        if new_status == 'resolved':
            alert.resolved_at = datetime.utcnow()
        db.session.add(alert)
        db.session.commit()
        return AlertSchema.dump(alert), 200
