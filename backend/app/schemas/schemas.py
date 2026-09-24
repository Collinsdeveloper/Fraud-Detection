class UserSchema:
    @staticmethod
    def dump(user):
        return {
            'user_id': user.user_id,
            'full_name': user.full_name,
            'email': user.email,
            'phone_number': user.phone_number,
            'role': user.role,
            'status': user.status,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        }


class SubscriberSchema:
    @staticmethod
    def dump(sub):
        return {
            'subscriber_id': sub.subscriber_id,
            'msisdn': sub.msisdn,
            'first_name': sub.first_name,
            'last_name': sub.last_name,
            'full_name': f"{sub.first_name or ''} {sub.last_name or ''}".strip() or None,
            'network': sub.network,
            'is_vip': sub.is_vip,
            'alert_channel': sub.alert_channel,
            'status': sub.status,
            'flagged_reason': sub.flagged_reason,
            'created_at': sub.created_at.isoformat() if sub.created_at else None,
            'updated_at': sub.updated_at.isoformat() if sub.updated_at else None,
        }


class SimSwapEventSchema:
    @staticmethod
    def dump(event):
        return {
            'event_id': event.event_id,
            'msisdn': event.msisdn,
            'old_imsi': event.old_imsi,
            'new_imsi': event.new_imsi,
            'old_iccid': event.old_iccid,
            'new_iccid': event.new_iccid,
            'device_model': event.device_model,
            'channel': event.channel,
            'agent_name': event.agent_name,
            'network_change': event.network_change,
            'swap_datetime': event.swap_datetime.isoformat() if event.swap_datetime else None,
            'risk_score': event.risk_score,
            'risk_level': event.risk_level,
            'reasons': event.reasons or [],
            'status': event.status,
            'created_at': event.created_at.isoformat() if event.created_at else None,
        }


class AirtimeTransferEventSchema:
    @staticmethod
    def dump(event):
        return {
            'event_id': event.event_id,
            'sender_msisdn': event.sender_msisdn,
            'recipient_msisdn': event.recipient_msisdn,
            'amount': event.amount,
            'method': event.method,
            'transfer_datetime': event.transfer_datetime.isoformat() if event.transfer_datetime else None,
            'is_new_recipient': event.is_new_recipient,
            'transfers_window_60m': event.transfers_window_60m,
            'risk_score': event.risk_score,
            'risk_level': event.risk_level,
            'reasons': event.reasons or [],
            'status': event.status,
            'created_at': event.created_at.isoformat() if event.created_at else None,
        }


class AccountEventSchema:
    @staticmethod
    def dump(event):
        return {
            'event_id': event.event_id,
            'msisdn': event.msisdn,
            'event_type': event.event_type,
            'device_hash': event.device_hash,
            'ip_address': event.ip_address,
            'location': event.location,
            'details': event.details,
            'event_datetime': event.event_datetime.isoformat() if event.event_datetime else None,
            'risk_score': event.risk_score,
            'risk_level': event.risk_level,
            'reasons': event.reasons or [],
            'status': event.status,
            'created_at': event.created_at.isoformat() if event.created_at else None,
        }


class AlertSchema:
    @staticmethod
    def dump(alert):
        return {
            'alert_id': alert.alert_id,
            'alert_type': alert.alert_type,
            'msisdn': alert.msisdn,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity,
            'risk_score': alert.risk_score,
            'status': alert.status,
            'channel_sent': alert.channel_sent,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
            'created_at': alert.created_at.isoformat() if alert.created_at else None,
        }


class NotificationLogSchema:
    @staticmethod
    def dump(log):
        return {
            'log_id': log.log_id,
            'alert_id': log.alert_id,
            'msisdn': log.msisdn,
            'channel': log.channel,
            'provider': log.provider,
            'request_payload': log.request_payload,
            'response_payload': log.response_payload,
            'success': log.success,
            'error': log.error,
            'created_at': log.created_at.isoformat() if log.created_at else None,
        }


class FraudRuleSchema:
    @staticmethod
    def dump(rule):
        return {
            'rule_id': rule.rule_id,
            'name': rule.name,
            'code': rule.code,
            'description': rule.description,
            'category': rule.category,
            'weight': rule.weight,
            'severity': rule.severity,
            'is_active': rule.is_active,
            'config': rule.config or {},
        }
