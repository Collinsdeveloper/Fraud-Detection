from datetime import datetime, timedelta

from flask_restful import Resource

from app import db
from ..models.models import (
    AccountEvent, AirtimeTransferEvent, Alert, NotificationLog,
    SimSwapEvent, Subscriber,
)
from ..utils.auth import staff_identity


def _series(model, column, days=7):
    """Count rows per day for the last `days` days (oldest first)."""
    start = datetime.utcnow() - timedelta(days=days - 1)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.session.query(
        db.func.date(column).label('day'),
        db.func.count().label('total'),
    ).filter(column >= start).group_by(db.func.date(column)).all()
    counts = {r.day.isoformat(): r.total for r in rows}
    return [
        {'date': (start + timedelta(days=i)).date().isoformat(),
         'count': counts.get((start + timedelta(days=i)).date().isoformat(), 0)}
        for i in range(days)
    ]


class DashboardSummary(Resource):
    """GET /dashboard/summary"""

    def get(self):
        identity, error = staff_identity()
        if error:
            return error

        open_alerts = Alert.query.filter_by(status='open').count()
        high_critical = Alert.query.filter(
            Alert.severity.in_(['HIGH', 'CRITICAL']),
            Alert.status != 'resolved',
        ).count()
        total_subscribers = Subscriber.query.count()
        flagged_subscribers = Subscriber.query.filter(
            Subscriber.status.in_(['flagged', 'blocked'])
        ).count()

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        sim_today = SimSwapEvent.query.filter(SimSwapEvent.swap_datetime >= today).count()
        airtime_today = AirtimeTransferEvent.query.filter(
            AirtimeTransferEvent.transfer_datetime >= today
        ).count()
        account_today = AccountEvent.query.filter(AccountEvent.event_datetime >= today).count()

        severity_dist = {
            row[0]: row[1] for row in (
                db.session.query(Alert.severity, db.func.count())
                .group_by(Alert.severity).all()
            )
        }
        for sev in ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'):
            severity_dist.setdefault(sev, 0)

        notification_stats = {
            'total': NotificationLog.query.count(),
            'successful': NotificationLog.query.filter_by(success=True).count(),
            'failed': NotificationLog.query.filter(NotificationLog.success.is_(False)).count(),
        }

        recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(8).all()
        watchlist = SimSwapEvent.query.filter(
            SimSwapEvent.risk_level.in_(['suspicious', 'flagged'])
        ).order_by(SimSwapEvent.swap_datetime.desc()).limit(6).all()

        return {
            'open_alerts': open_alerts,
            'high_critical': high_critical,
            'total_subscribers': total_subscribers,
            'flagged_subscribers': flagged_subscribers,
            'events_today': {
                'sim_swaps': sim_today,
                'airtime_transfers': airtime_today,
                'account_events': account_today,
            },
            'severity_distribution': severity_dist,
            'sim_swap_trend': _series(SimSwapEvent, SimSwapEvent.swap_datetime),
            'airtime_trend': _series(AirtimeTransferEvent, AirtimeTransferEvent.transfer_datetime),
            'account_trend': _series(AccountEvent, AccountEvent.event_datetime),
            'notifications': notification_stats,
            'recent_alerts': [
                {
                    'alert_id': a.alert_id,
                    'alert_type': a.alert_type,
                    'msisdn': a.msisdn,
                    'title': a.title,
                    'severity': a.severity,
                    'risk_score': a.risk_score,
                    'status': a.status,
                    'created_at': a.created_at.isoformat() if a.created_at else None,
                }
                for a in recent_alerts
            ],
            'active_watchlist': [
                {
                    'event_id': s.event_id,
                    'msisdn': s.msisdn,
                    'risk_score': s.risk_score,
                    'risk_level': s.risk_level,
                    'channel': s.channel,
                    'swap_datetime': s.swap_datetime.isoformat() if s.swap_datetime else None,
                    'reasons': s.reasons or [],
                }
                for s in watchlist
            ],
        }, 200
