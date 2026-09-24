from flask_restful import Resource, request

from ..models.models import NotificationLog
from ..schemas.schemas import NotificationLogSchema
from ..services.notification_service import send_test
from ..utils.auth import staff_identity
from ..utils.helpers import normalize_msisdn, paginate


class TestNotification(Resource):
    """POST /notifications/test  {msisdn, channel: sms|voice}"""

    def post(self):
        identity, error = staff_identity()
        if error:
            return error
        data = request.get_json(force=True) or {}
        msisdn = data.get('msisdn')
        channel = (data.get('channel') or 'sms').lower()
        if not msisdn:
            return {'message': 'msisdn is required'}, 400
        if channel not in ('sms', 'voice'):
            return {'message': 'channel must be sms or voice'}, 400

        result = send_test(normalize_msisdn(msisdn), channel)
        return {
            'message': 'Test %s dispatched to %s' % (channel.upper(), normalize_msisdn(msisdn)),
            'success': bool(result.get('success')),
            'response': result.get('response'),
            'error': result.get('error'),
            'simulated': bool(result.get('provider_simulated')),
        }, 200


class NotificationLogList(Resource):
    """GET /notifications/logs"""

    def get(self):
        identity, error = staff_identity()
        if error:
            return error
        query = NotificationLog.query.order_by(NotificationLog.created_at.desc())
        if request.args.get('channel'):
            query = query.filter(NotificationLog.channel == request.args['channel'].upper())
        if request.args.get('success') in ('true', 'false', '1', '0'):
            query = query.filter(NotificationLog.success == (request.args['success'] in ('true', '1')))
        return paginate(query, NotificationLogSchema.dump), 200
