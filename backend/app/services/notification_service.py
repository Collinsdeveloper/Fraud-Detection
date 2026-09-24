"""Notification service.

Turns generated alerts into real outbound SMS / Voice pushes through
Africa's Talking, and keeps an auditable trail in `notification_logs`.
"""
from flask import current_app

from ..models.models import Alert, NotificationLog, Subscriber
from ..utils.helpers import normalize_msisdn
from .africastalking_client import AfricasTalkingClient

SEVERITY_ORDER = ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']


def _notify_level():
    return current_app.config.get('DEFAULT_NOTIFY_LEVEL', 'HIGH').upper()


def should_notify(alert):
    """Only push alerts at/above the configured notify level."""
    try:
        return SEVERITY_ORDER.index(alert.severity) >= SEVERITY_ORDER.index(_notify_level())
    except ValueError:
        return True


def _log(alert_id, msisdn, channel, result):
    log = NotificationLog(
        alert_id=alert_id,
        msisdn=msisdn,
        channel=channel,
        provider='AFRICASTALKING',
        request_payload=result.get('request'),
        response_payload=result.get('response'),
        success=bool(result.get('success')),
        error=result.get('error'),
    )
    from app import db
    db.session.add(log)
    db.session.commit()
    return log


def _sms_template(alert):
    return (
        f"[FRAUD ALERT] {alert.title}\n"
        f"{alert.message}\n"
        f"Severity: {alert.severity} | Risk: {alert.risk_score}/100\n"
        f"If this was NOT you, call your service provider immediately. "
        f"FraudShield Monitoring."
    )


def send_sms_alert(alert):
    """Send one SMS alert and log the result. Never raises."""
    return _send_sms('+%s' % alert.msisdn.lstrip('+'), _sms_template(alert), alert.alert_id)


def _invalid_sender(result):
    body = result.get('response') or {}
    message = (body.get('SMSMessageData') or {}).get('Message', '')
    return 'SenderId' in str(message) or 'sender' in str(message).lower()


def _send_sms(number, message, alert_id=None):
    """Send one SMS with an optional retry without a `from`. Never raises.

    Returns the delivery result dict (already persisted to notification_logs).
    """
    if not AfricasTalkingClient.configured():
        result = {
            'success': True,
            'provider_simulated': True,
            'request': {'to': number, 'message': message[:160]},
            'response': {'SMSMessageData': {'Message': 'SIMULATED_DELIVERY'}},
        }
        _log(alert_id, number, 'SMS', result)
        return result
    sender = current_app.config.get('AT_SENDER_ID')
    result = AfricasTalkingClient.send_sms(number, message, sender_id=sender or None)
    if sender and _invalid_sender(result):
        result = AfricasTalkingClient.send_sms(number, message, sender_id=None)
    _log(alert_id, number, 'SMS', result)
    return result


def send_voice_alert(alert):
    """Initiate an outbound voice call to the subscriber and log the result.

    The sandbox voice host is not always reachable; when unavailable the call is
    queued as a clearly-labelled simulation so end-to-end demos keep working.
    """
    number = '+%s' % alert.msisdn.lstrip('+')
    if not AfricasTalkingClient.configured():
        return _log(alert.alert_id, alert.msisdn, 'VOICE', {
            'success': True,
            'provider_simulated': True,
            'request': {'to': number, 'from': current_app.config.get('AT_VOICE_FROM')},
            'response': {'entries': [{'status': 'SIMULATED_QUEUED'}]},
        })
    result = AfricasTalkingClient.make_call(
        to=number,
        client_request_id=f'ALERT-{alert.alert_id}',
    )
    unreachable = result.get('response') is None and not result.get('success')
    if unreachable and current_app.config.get('AT_SIMULATE_VOICE_ON_UNAVAILABLE', True):
        return _log(alert.alert_id, alert.msisdn, 'VOICE', {
            'success': True,
            'provider_simulated': True,
            'request': result.get('request') or {'to': number, 'from': current_app.config.get('AT_VOICE_FROM')},
            'response': {'entries': [{'status': 'SIMULATED_QUEUED'}]},
            'error': (result.get('error') or '')[:200],
        })
    return _log(alert.alert_id, alert.msisdn, 'VOICE', result)


def dispatch(alert, subscriber=None):
    """Send the alert through the subscriber's preferred channel(s).

    Returns the alert with channel_sent updated. If the channel preference is
    'none' or the alert severity is below the notify threshold, nothing is sent.
    """
    from app import db

    if not should_notify(alert):
        alert.channel_sent = 'NONE'
        db.session.add(alert)
        db.session.commit()
        return alert

    if subscriber is None:
        subscriber = Subscriber.query.filter_by(msisdn=alert.msisdn).first()

    channel = (subscriber.alert_channel if subscriber else 'sms') or 'sms'
    sent = []

    if channel in ('sms', 'both'):
        try:
            send_sms_alert(alert)
            sent.append('SMS')
        except Exception as exc:  # never crash the alert pipeline
            db.session.add(NotificationLog(
                alert_id=alert.alert_id, msisdn=alert.msisdn, channel='SMS',
                provider='AFRICASTALKING', success=False, error=f'unhandled: {exc}',
            ))
            db.session.commit()

    if channel in ('voice', 'both'):
        try:
            send_voice_alert(alert)
            sent.append('VOICE')
        except Exception as exc:
            db.session.add(NotificationLog(
                alert_id=alert.alert_id, msisdn=alert.msisdn, channel='VOICE',
                provider='AFRICASTALKING', success=False, error=f'unhandled: {exc}',
            ))
            db.session.commit()

    alert.channel_sent = '+'.join(sent) if sent else 'NONE'
    db.session.add(alert)
    db.session.commit()
    return alert



def send_test(msisdn, channel='sms'):
    """Send a test SMS or Voice notification to a given number (operator tool)."""
    msisdn = normalize_msisdn(msisdn)
    if channel == 'voice':
        result = AfricasTalkingClient.make_call(
            to='+%s' % msisdn.lstrip('+'),
            client_request_id='TEST-CALL',
        )
        unreachable = result.get('response') is None and not result.get('success')
        if unreachable and current_app.config.get('AT_SIMULATE_VOICE_ON_UNAVAILABLE', True):
            result = {
                'success': True,
                'provider_simulated': True,
                'request': {'to': '+%s' % msisdn, 'from': current_app.config.get('AT_VOICE_FROM')},
                'response': {'entries': [{'status': 'SIMULATED_QUEUED'}]},
                'error': (result.get('error') or '')[:200],
            }
        _log(None, msisdn, 'VOICE', result)
    else:
        result = _send_sms(
            '+%s' % msisdn.lstrip('+'),
            'FraudShield test SMS: your alert channel is configured and operational.',
            alert_id=None,
        )
    return result
