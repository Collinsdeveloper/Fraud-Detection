"""Alert lifecycle: create an Alert row, dispatch SMS/Voice and update the
subscriber's standing where appropriate.
"""
from .notification_service import dispatch
from .risk_engine import severity_for


def raise_alert(alert_type, msisdn, title, message, risk_score, level,
                flag_subscriber=False, flag_reason=None):
    """Create + dispatch an alert. Returns the Alert instance."""
    from app import db
    from ..models.models import Alert, Subscriber

    alert = Alert(
        alert_type=alert_type,
        msisdn=msisdn,
        title=title,
        message=message,
        severity=severity_for(level, risk_score),
        risk_score=risk_score,
        status='open',
    )
    db.session.add(alert)
    db.session.flush()   # get alert_id for the notification log FK

    subscriber = Subscriber.query.filter_by(msisdn=msisdn).first()
    if flag_subscriber and subscriber and subscriber.status == 'active':
        subscriber.status = 'flagged'
        subscriber.flagged_reason = flag_reason or title
        db.session.add(subscriber)

    db.session.commit()
    dispatch(alert, subscriber)
    return alert
