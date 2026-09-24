"""Real-time fraud detection engine.

Every inbound event is scored against a series of configurable rules stored in
the `fraud_rules` table. The engine returns a risk score (0-100), a risk level
(safe / suspicious / flagged) and a human-readable list of reasons for the
analyst console and for subscriber SMS/Voice alerts.

Risk levels:
    safe        score 0-29
    suspicious  score 30-59   -> MEDIUM alert
    flagged     score 60+     -> HIGH alert (CRITICAL at 85+)
"""
from datetime import datetime, timedelta

from ..models.models import (
    AccountEvent, AirtimeTransferEvent, FraudRule, SimSwapEvent, Subscriber,
)

LEVEL_SAFE = 'safe'
LEVEL_SUSPICIOUS = 'suspicious'
LEVEL_FLAGGED = 'flagged'


# --------------------------------------------------------------------------- #
#  Rule helpers
# --------------------------------------------------------------------------- #
def _rule(code):
    return FraudRule.query.filter_by(code=code, is_active=True).first()


def _active(code):
    """Return True when the given rule code is active in the DB."""
    return FraudRule.query.filter_by(code=code, is_active=True).first() is not None


def _weight(code, default_weight, default_config=None):
    """Return (weight, config) for a rule, falling back to sane defaults."""
    rule = _rule(code)
    if rule:
        return rule.weight, (rule.config or {})
    return default_weight, (default_config or {})


def _cfg(config, key, default):
    return config.get(key, default)


def _odd_hour(dt, start_hour=0, end_hour=5):
    return dt is not None and start_hour <= dt.hour <= end_hour


def classify(score):
    if score >= 60:
        return LEVEL_FLAGGED
    if score >= 30:
        return LEVEL_SUSPICIOUS
    return LEVEL_SAFE


def severity_for(level, score):
    if level == LEVEL_FLAGGED:
        return 'CRITICAL' if score >= 85 else 'HIGH'
    if level == LEVEL_SUSPICIOUS:
        return 'MEDIUM'
    return 'LOW'


def active_flag_for(msisdn, hours_back=24):
    """True when the line has a recent FLAGGED sim-swap or is flagged by an analyst."""
    sub = Subscriber.query.filter_by(msisdn=msisdn).first()
    if sub and sub.status == 'flagged':
        return True
    since = datetime.utcnow() - timedelta(hours=hours_back)
    recent = SimSwapEvent.query.filter(
        SimSwapEvent.msisdn == msisdn,
        SimSwapEvent.risk_level == LEVEL_FLAGGED,
        SimSwapEvent.swap_datetime >= since,
    ).first()
    return recent is not None


# --------------------------------------------------------------------------- #
#  SIM swap scoring
# --------------------------------------------------------------------------- #
def evaluate_sim_swap(event):
    """Score a SimSwapEvent row. Returns dict(score, level, reasons)."""
    score = 0
    reasons = []

    # 1. Repeat SIM swap inside a short window -- classic fraud enabler
    if _active('SIM_SWAP_REPEAT'):
        weight, config = _weight('SIM_SWAP_REPEAT', 45, {'max_days': 30})
        max_days = _cfg(config, 'max_days', 30)
        prev = SimSwapEvent.query.filter(
            SimSwapEvent.msisdn == event.msisdn,
            SimSwapEvent.event_id != event.event_id,
            SimSwapEvent.swap_datetime < event.swap_datetime,
        ).order_by(SimSwapEvent.swap_datetime.desc()).first()
        if prev:
            delta_days = (event.swap_datetime - prev.swap_datetime).total_seconds() / 86400.0
            if 0 <= delta_days <= max_days:
                score += weight
                reasons.append(
                    f'Repeat SIM swap only {delta_days:.1f}d after the previous swap '
                    f'(threshold {int(max_days)}d)'
                )

    # 2. Risky request channel (in-person agent / SIM toolkit / remote)
    if _active('SIM_SWAP_CHANNEL'):
        weight, config = _weight('SIM_SWAP_CHANNEL', 25, {'channels': ['AGENT', 'SIM_TOOLKIT', 'WHATSAPP']})
        risky = _cfg(config, 'channels', ['AGENT', 'SIM_TOOLKIT', 'WHATSAPP'])
        if event.channel and event.channel.upper() in [c.upper() for c in risky]:
            score += weight
            reasons.append(f'SIM swap requested via high-risk channel "{event.channel}"')

    # 3. Swap executed at an odd hour
    if _active('SIM_SWAP_ODD_HOUR'):
        weight, config = _weight('SIM_SWAP_ODD_HOUR', 20, {'start': 0, 'end': 5})
        if _odd_hour(event.swap_datetime, _cfg(config, 'start', 0), _cfg(config, 'end', 5)):
            score += weight
            reasons.append(
                f'Swap executed at {event.swap_datetime.strftime("%H:%M")} (off-business hours)'
            )

    # 4. Network change (new IMSI belongs to a different MNC)
    if _active('SIM_SWAP_NETWORK_CHANGE'):
        weight, _ = _weight('SIM_SWAP_NETWORK_CHANGE', 20)
        if event.network_change:
            score += weight
            reasons.append('New SIM operates on a different network (MNC change)')

    # 5. VIP subscriber line is a high-value target
    if _active('SIM_SWAP_VIP'):
        weight, _ = _weight('SIM_SWAP_VIP', 20)
        sub = Subscriber.query.filter_by(msisdn=event.msisdn).first()
        if sub and sub.is_vip:
            score += weight
            reasons.append('VIP / high-value subscriber line involved')

    # 6. Fresh line swapped almost immediately after onboarding
    if _active('SIM_SWAP_ACCOUNT_AGE'):
        weight, config = _weight('SIM_SWAP_ACCOUNT_AGE', 30, {'max_days': 7})
        sub = Subscriber.query.filter_by(msisdn=event.msisdn).first()
        if sub and sub.created_at:
            age_days = (event.swap_datetime - sub.created_at).total_seconds() / 86400.0
            if 0 <= age_days <= _cfg(config, 'max_days', 7):
                score += weight
                reasons.append(f'Line swapped only {age_days:.1f}d after registration')

    score = min(score, 100)
    return {'score': score, 'level': classify(score), 'reasons': reasons}


# --------------------------------------------------------------------------- #
#  Airtime transfer scoring
# --------------------------------------------------------------------------- #
def evaluate_airtime(event):
    score = 0
    reasons = []

    # 1. Unusually large amount
    if _active('AIRTIME_AMOUNT'):
        weight, config = _weight('AIRTIME_AMOUNT', 25, {'min_amount': 500})
        if event.amount >= _cfg(config, 'min_amount', 500):
            score += weight
            reasons.append(f'Large airtime amount KES {event.amount:,.0f}')

    # 2. First-ever transfer to this recipient
    if _active('AIRTIME_NEW_RECIPIENT'):
        weight, _ = _weight('AIRTIME_NEW_RECIPIENT', 30)
        if event.is_new_recipient:
            score += weight
            reasons.append(f'First recorded transfer to {event.recipient_msisdn}')

    # 3. Velocity -- many transfers in a short window (liquidation pattern)
    if _active('AIRTIME_VELOCITY'):
        weight, config = _weight('AIRTIME_VELOCITY', 35, {'window_min': 60, 'count': 5})
        window = _cfg(config, 'window_min', 60)
        limit = _cfg(config, 'count', 5)
        if event.transfers_window_60m >= limit:
            score += weight
            reasons.append(
                f'{event.transfers_window_60m} transfers from this line in the last '
                f'{window} minutes (limit {limit})'
            )

    # 4. Odd-hour transfer
    if _active('AIRTIME_ODD_HOUR'):
        weight, config = _weight('AIRTIME_ODD_HOUR', 15, {'start': 0, 'end': 5})
        if _odd_hour(event.transfer_datetime, _cfg(config, 'start', 0), _cfg(config, 'end', 5)):
            score += weight
            reasons.append(f'Transfer executed at {event.transfer_datetime.strftime("%H:%M")}')

    # 5. Sender line has an active fraud flag (recent flagged SIM swap)
    if _active('AIRTIME_FLAGGED_LINE'):
        weight, _ = _weight('AIRTIME_FLAGGED_LINE', 40)
        if active_flag_for(event.sender_msisdn):
            score += weight
            reasons.append('Sender line is currently under a fraud watch (recent SIM swap)')

    score = min(score, 100)
    return {'score': score, 'level': classify(score), 'reasons': reasons}


# --------------------------------------------------------------------------- #
#  Account takeover (ATO) scoring
# --------------------------------------------------------------------------- #
def evaluate_account(event):
    score = 0
    reasons = []
    event_type = (event.event_type or '').upper()

    # 1. Sensitive account-changing events
    sensitive_map = {
        'PIN_CHANGE': ('ACCOUNT_PIN_CHANGE', 30),
        'PASSWORD_RESET': ('ACCOUNT_PASSWORD_RESET', 25),
        'BENEFICIARY_CHANGE': ('ACCOUNT_BENEFICIARY_CHANGE', 35),
        'PROFILE_CHANGE': ('ACCOUNT_PROFILE_CHANGE', 20),
        'NEW_DEVICE': ('ACCOUNT_NEW_DEVICE', 25),
    }
    for kind, (code, default_w) in sensitive_map.items():
        if event_type == kind and _active(code):
            weight, _ = _weight(code, default_w)
            score += weight
            reasons.append(f'Account altering event: {kind.replace("_", " ").title()}')

    # 2. OTP storm -- several OTP generations in a short window (SIM hijack probe)
    if event_type in ('LOGIN_OTP', 'OTP_REQUEST', 'LOGIN') and _active('ACCOUNT_OTP_STORM'):
        weight, config = _weight('ACCOUNT_OTP_STORM', 40, {'window_min': 15, 'count': 3})
        window_min = _cfg(config, 'window_min', 15)
        limit = _cfg(config, 'count', 3)
        since = event.event_datetime - timedelta(minutes=window_min)
        count = AccountEvent.query.filter(
            AccountEvent.msisdn == event.msisdn,
            AccountEvent.event_type.in_(['LOGIN_OTP', 'OTP_REQUEST', 'LOGIN']),
            AccountEvent.event_datetime >= since,
            AccountEvent.event_datetime <= event.event_datetime,
        ).count()
        if count >= limit:
            score += weight
            reasons.append(
                f'{count} login/OTP events in the last {window_min} minutes (limit {limit})'
            )

    # 3. PIN change rapidly followed by OTP / login (classic ATO sequence)
    if event_type in ('LOGIN_OTP', 'OTP_REQUEST') and _active('ACCOUNT_PIN_PLUS_OTP'):
        weight, config = _weight('ACCOUNT_PIN_PLUS_OTP', 55, {'window_min': 10})
        window_min = _cfg(config, 'window_min', 10)
        since = event.event_datetime - timedelta(minutes=window_min)
        pin_before = AccountEvent.query.filter(
            AccountEvent.msisdn == event.msisdn,
            AccountEvent.event_type == 'PIN_CHANGE',
            AccountEvent.event_datetime >= since,
            AccountEvent.event_datetime < event.event_datetime,
        ).first()
        if pin_before:
            score += weight
            reasons.append(f'PIN change followed by an OTP attempt within {window_min} minutes')

    # 4. Odd-hour account activity
    if _active('ACCOUNT_ODD_HOUR'):
        weight, config = _weight('ACCOUNT_ODD_HOUR', 15, {'start': 0, 'end': 5})
        if _odd_hour(event.event_datetime, _cfg(config, 'start', 0), _cfg(config, 'end', 5)):
            score += weight
            reasons.append(f'Account activity at {event.event_datetime.strftime("%H:%M")}')

    # 5. Line currently under watch gets extra weight
    if _active('ACCOUNT_FLAGGED_LINE'):
        weight, _ = _weight('ACCOUNT_FLAGGED_LINE', 35)
        if active_flag_for(event.msisdn):
            score += weight
            reasons.append('Line is currently under a fraud watch')

    score = min(score, 100)
    return {'score': score, 'level': classify(score), 'reasons': reasons}


# --------------------------------------------------------------------------- #
#  Entry points used by the controllers
# --------------------------------------------------------------------------- #
def evaluate(kind, event):
    """Dispatch an event instance to the correct scorer."""
    if kind == 'SIM_SWAP':
        return evaluate_sim_swap(event)
    if kind == 'AIRTIME':
        return evaluate_airtime(event)
    if kind == 'ACCOUNT':
        return evaluate_account(event)
    raise ValueError(f'Unknown event kind: {kind}')

