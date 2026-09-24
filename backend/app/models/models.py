from datetime import datetime

from app import db


def utcnow():
    """Naive UTC timestamp used across the schema."""
    return datetime.utcnow()


class User(db.Model):
    """Operator of the fraud-monitoring console (admin / analyst)."""
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False, default='analyst')  # admin | analyst
    status = db.Column(db.String(20), nullable=False, default='active')  # active | disabled
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f'<User {self.email}>'


class Subscriber(db.Model):
    """A mobile subscriber whose line is being watched."""
    __tablename__ = 'subscribers'

    subscriber_id = db.Column(db.Integer, primary_key=True)
    msisdn = db.Column(db.String(30), unique=True, index=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    network = db.Column(db.String(40), default='SAFARICOM')  # SAFARICOM | AIRTEL | TELKOM | EQUITEL
    is_vip = db.Column(db.Boolean, default=False, nullable=False)
    alert_channel = db.Column(db.String(10), default='sms', nullable=False)  # sms | voice | both | none
    status = db.Column(db.String(20), default='active', nullable=False)      # active | flagged | blocked
    flagged_reason = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f'<Subscriber {self.msisdn}>'


class SimSwapEvent(db.Model):
    """A SIM-swap (SIM re-issuance) event captured from the telco core."""
    __tablename__ = 'sim_swap_events'

    event_id = db.Column(db.Integer, primary_key=True)
    msisdn = db.Column(db.String(30), index=True, nullable=False)
    old_imsi = db.Column(db.String(20), nullable=True)
    new_imsi = db.Column(db.String(20), nullable=True)
    old_iccid = db.Column(db.String(24), nullable=True)
    new_iccid = db.Column(db.String(24), nullable=True)
    device_model = db.Column(db.String(80), nullable=True)
    channel = db.Column(db.String(30), nullable=True)   # AGENT | SIM_TOOLKIT | WEB | RETAILER | WHATSAPP
    agent_name = db.Column(db.String(80), nullable=True)
    network_change = db.Column(db.Boolean, default=False, nullable=False)
    swap_datetime = db.Column(db.DateTime, nullable=False)
    risk_score = db.Column(db.Integer, default=0, nullable=False)
    risk_level = db.Column(db.String(20), default='safe', nullable=False)  # safe | suspicious | flagged
    reasons = db.Column(db.JSON, default=list)
    status = db.Column(db.String(20), default='open', nullable=False)      # open | resolved
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f'<SimSwap {self.msisdn} {self.risk_level}>'


class AirtimeTransferEvent(db.Model):
    """An airtime transfer between two subscribers."""
    __tablename__ = 'airtime_transfer_events'

    event_id = db.Column(db.Integer, primary_key=True)
    sender_msisdn = db.Column(db.String(30), index=True, nullable=False)
    recipient_msisdn = db.Column(db.String(30), index=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), nullable=True)  # USSD | APP | DIAL_CODE | VENDOR
    transfer_datetime = db.Column(db.DateTime, nullable=False)
    is_new_recipient = db.Column(db.Boolean, default=False, nullable=False)
    transfers_window_60m = db.Column(db.Integer, default=0, nullable=False)
    risk_score = db.Column(db.Integer, default=0, nullable=False)
    risk_level = db.Column(db.String(20), default='safe', nullable=False)
    reasons = db.Column(db.JSON, default=list)
    status = db.Column(db.String(20), default='open', nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f'<Airtime {self.sender_msisdn} -> {self.recipient_msisdn} {self.amount}>'


class AccountEvent(db.Model):
    """Account activity that could signal an account takeover (ATO)."""
    __tablename__ = 'account_events'

    event_id = db.Column(db.Integer, primary_key=True)
    msisdn = db.Column(db.String(30), index=True, nullable=False)
    event_type = db.Column(db.String(40), nullable=False)  # LOGIN | LOGIN_OTP | PIN_CHANGE | PASSWORD_RESET | PROFILE_CHANGE | NEW_DEVICE | BENEFICIARY_CHANGE
    device_hash = db.Column(db.String(80), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    details = db.Column(db.JSON)  # event-specific metadata
    event_datetime = db.Column(db.DateTime, nullable=False)
    risk_score = db.Column(db.Integer, default=0, nullable=False)
    risk_level = db.Column(db.String(20), default='safe', nullable=False)
    reasons = db.Column(db.JSON, default=list)
    status = db.Column(db.String(20), default='open', nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f'<AccountEvent {self.msisdn} {self.event_type}>'


class Alert(db.Model):
    """A generated fraud alert that is pushed to the subscriber (SMS/Voice)."""
    __tablename__ = 'alerts'

    alert_id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(40), nullable=False)  # SIM_SWAP | AIRTIME_TRANSFER | ACCOUNT_TAKEOVER
    msisdn = db.Column(db.String(30), index=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # INFO | LOW | MEDIUM | HIGH | CRITICAL
    risk_score = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default='open', nullable=False)  # open | acknowledged | resolved
    channel_sent = db.Column(db.String(10), default='NONE', nullable=False)  # NONE | SMS | VOICE | BOTH
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f'<Alert {self.alert_type} {self.severity} {self.msisdn}>'


class NotificationLog(db.Model):
    """Record of every delivery attempt through Africa's Talking."""
    __tablename__ = 'notification_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('alerts.alert_id'), nullable=True)
    msisdn = db.Column(db.String(30), index=True, nullable=False)
    channel = db.Column(db.String(10), nullable=False)  # SMS | VOICE
    provider = db.Column(db.String(30), nullable=False)  # AFRICASTALKING | SIMULATED
    request_payload = db.Column(db.JSON)
    response_payload = db.Column(db.JSON)
    success = db.Column(db.Boolean, default=False, nullable=False)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f'<NotificationLog {self.channel} {self.msisdn} success={self.success}>'


class FraudRule(db.Model):
    """Configurable detection rule consumed by the risk engine."""
    __tablename__ = 'fraud_rules'

    rule_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(20), nullable=False)  # SIM_SWAP | AIRTIME | ACCOUNT
    weight = db.Column(db.Integer, default=20, nullable=False)   # risk points when triggered
    severity = db.Column(db.String(20), default='MEDIUM', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    config = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f'<FraudRule {self.code} {self.weight}>'
