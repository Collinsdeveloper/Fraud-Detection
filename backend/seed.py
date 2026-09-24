"""Seed the FraudShield database with demo data (idempotent).

Usage:
    ./venv/bin/python seed.py

Creates tables (db.create_all), an admin + analyst account, demo subscribers,
the default fraud-detection rule set, and historical events so the dashboard
comes alive immediately.
"""
from datetime import datetime, timedelta

from app import create_app, db, bcrypt
from app.models.models import (
    AccountEvent, AirtimeTransferEvent, Alert, FraudRule, NotificationLog,
    SimSwapEvent, Subscriber, User,
)

app = create_app()


def now():
    return datetime.utcnow()


RULES = [
    # ---- SIM SWAP ----
    dict(name='Repeat SIM swap window', code='SIM_SWAP_REPEAT', category='SIM_SWAP',
         description='A second SIM swap on the same line within N days is a classic fraud enabler.',
         weight=45, severity='HIGH', config={'max_days': 30}),
    dict(name='High-risk swap channel', code='SIM_SWAP_CHANNEL', category='SIM_SWAP',
         description='Swaps requested via in-person agents, SIM toolkit or chat remote support.',
         weight=25, severity='MEDIUM', config={'channels': ['AGENT', 'SIM_TOOLKIT', 'WHATSAPP']}),
    dict(name='Off-hours swap', code='SIM_SWAP_ODD_HOUR', category='SIM_SWAP',
         description='Swap executed between midnight and 06:00 local.',
         weight=20, severity='MEDIUM', config={'start': 0, 'end': 5}),
    dict(name='Network (MNC) change', code='SIM_SWAP_NETWORK_CHANGE', category='SIM_SWAP',
         description='New SIM runs on a different mobile network than the previous one.',
         weight=20, severity='MEDIUM', config={}),
    dict(name='VIP line swap', code='SIM_SWAP_VIP', category='SIM_SWAP',
         description='Profile is marked VIP / high-value.',
         weight=20, severity='MEDIUM', config={}),
    dict(name='Fresh line swap', code='SIM_SWAP_ACCOUNT_AGE', category='SIM_SWAP',
         description='Line swapped within N days of subscriber onboarding.',
         weight=30, severity='HIGH', config={'max_days': 7}),
    # ---- AIRTIME ----
    dict(name='Large transfer amount', code='AIRTIME_AMOUNT', category='AIRTIME',
         description='Transfer at or above the configured amount threshold.',
         weight=25, severity='MEDIUM', config={'min_amount': 500}),
    dict(name='New recipient', code='AIRTIME_NEW_RECIPIENT', category='AIRTIME',
         description='Sender transfers to a recipient they have never paid before.',
         weight=30, severity='MEDIUM', config={}),
    dict(name='Transfer velocity', code='AIRTIME_VELOCITY', category='AIRTIME',
         description='Too many transfers from one line inside a short window (cash-out pattern).',
         weight=35, severity='HIGH', config={'window_min': 60, 'count': 5}),
    dict(name='Off-hours transfer', code='AIRTIME_ODD_HOUR', category='AIRTIME',
         description='Transfer executed between midnight and 06:00 local.',
         weight=15, severity='LOW', config={'start': 0, 'end': 5}),
    dict(name='Transfer from flagged line', code='AIRTIME_FLAGGED_LINE', category='AIRTIME',
         description='Sender has an active fraud watch (recent flagged SIM swap).',
         weight=40, severity='CRITICAL', config={}),
    # ---- ACCOUNT TAKEOVER ----
    dict(name='PIN change', code='ACCOUNT_PIN_CHANGE', category='ACCOUNT',
         description='Account PIN changed without prior identity confirmation.',
         weight=30, severity='HIGH', config={}),
    dict(name='Password reset', code='ACCOUNT_PASSWORD_RESET', category='ACCOUNT',
         description='Self-service password reset performed.',
         weight=25, severity='MEDIUM', config={}),
    dict(name='Beneficiary change', code='ACCOUNT_BENEFICIARY_CHANGE', category='ACCOUNT',
         description='Transfer beneficiary list modified.',
         weight=35, severity='HIGH', config={}),
    dict(name='Profile change', code='ACCOUNT_PROFILE_CHANGE', category='ACCOUNT',
         description='Account profile details updated.',
         weight=20, severity='MEDIUM', config={}),
    dict(name='New device', code='ACCOUNT_NEW_DEVICE', category='ACCOUNT',
         description='Login from a previously unseen device.',
         weight=25, severity='MEDIUM', config={}),
    dict(name='OTP storm', code='ACCOUNT_OTP_STORM', category='ACCOUNT',
         description='Many OTP requests in a short window - SIM hijack probing.',
         weight=40, severity='HIGH', config={'window_min': 15, 'count': 3}),
    dict(name='PIN + OTP sequence', code='ACCOUNT_PIN_PLUS_OTP', category='ACCOUNT',
         description='PIN change immediately followed by an OTP attempt.',
         weight=55, severity='CRITICAL', config={'window_min': 10}),
    dict(name='Off-hours account activity', code='ACCOUNT_ODD_HOUR', category='ACCOUNT',
         description='Account activity between midnight and 06:00 local.',
         weight=15, severity='LOW', config={'start': 0, 'end': 5}),
    dict(name='Activity on flagged line', code='ACCOUNT_FLAGGED_LINE', category='ACCOUNT',
         description='Account events on a line under an active fraud watch.',
         weight=35, severity='CRITICAL', config={}),
]


def seed_users():
    print('  - users')
    users = [
        dict(full_name='System Administrator', email='admin@fraudshield.io',
             phone_number='254712000001', role='admin', password='Admin@123'),
        dict(full_name='Security Analyst', email='analyst@fraudshield.io',
             phone_number='254712000002', role='analyst', password='Analyst@123'),
    ]
    for u in users:
        if User.query.filter_by(email=u['email']).first():
            continue
        db.session.add(User(
            full_name=u['full_name'], email=u['email'], phone_number=u['phone_number'],
            password_hash=bcrypt.generate_password_hash(u['password']).decode('utf-8'),
            role=u['role'], status='active',
        ))
    db.session.commit()


def seed_rules():
    print('  - fraud rules')
    for r in RULES:
        if FraudRule.query.filter_by(code=r['code']).first():
            continue
        db.session.add(FraudRule(**r))
    db.session.commit()


def seed_subscribers():
    print('  - subscribers')
    subs = [
        dict(msisdn='254722111222', first_name='Brian', last_name='Otieno', network='SAFARICOM',
             is_vip=True, alert_channel='both'),
        dict(msisdn='254733333444', first_name='Wanjiru', last_name='Kamau', network='AIRTEL',
             is_vip=False, alert_channel='sms'),
        dict(msisdn='254701555666', first_name='Dennis', last_name='Mwangi', network='SAFARICOM',
             is_vip=False, alert_channel='sms'),
        dict(msisdn='254745777888', first_name='Amina', last_name='Hassan', network='TELKOM',
             is_vip=False, alert_channel='voice'),
        dict(msisdn='254729999000', first_name='Kevin', last_name='Omondi', network='EQUITEL',
             is_vip=False, alert_channel='sms'),
        dict(msisdn='254710123456', first_name='Grace', last_name='Njeri', network='SAFARICOM',
             is_vip=False, alert_channel='sms'),
    ]
    for s in subs:
        if Subscriber.query.filter_by(msisdn=s['msisdn']).first():
            continue
        db.session.add(Subscriber(**s))
    db.session.commit()


def seed_events():
    print('  - historical events & alerts')
    if SimSwapEvent.query.count() == 0:
        base = now()
        swaps = [
            # (msisdn, channel, agent, days_ago, risk_level)
            ('254722111222', 'WEB', None, 60, 'safe'),
            ('254722111222', 'APP', None, 2, 'flagged'),    # repeat swap -> flagged
            ('254701555666', 'RETAILER', None, 20, 'safe'),
            ('254733333444', 'SIM_TOOLKIT', None, 33, 'suspicious'),
            ('254710123456', 'AGENT', 'Peter O.', 1, 'flagged'),
        ]
        for i, (msisdn, channel, agent, days, _level) in enumerate(swaps):
            db.session.add(SimSwapEvent(
                msisdn=msisdn,
                old_imsi='639021234567890' if i % 2 == 0 else '639031234567890',
                new_imsi='639031234567897' if channel in ('AGENT', 'SIM_TOOLKIT') else '639021234567899',
                old_iccid='8963911234567890123',
                new_iccid='8963911234567890999',
                device_model='Tecno Spark 20',
                channel=channel,
                agent_name=agent,
                network_change=channel in ('AGENT', 'SIM_TOOLKIT'),
                swap_datetime=base - timedelta(days=days, hours=2),
                risk_level=_level,
                risk_score=70 if _level == 'flagged' else (45 if _level == 'suspicious' else 0),
                reasons=['Repeat SIM swap within window'] if _level == 'flagged'
                        else (['High-risk channel'] if _level == 'suspicious' else []),
                status='open',
            ))
        db.session.commit()

    if AccountEvent.query.count() == 0:
        base = now()
        events = [
            ('254710123456', 'PIN_CHANGE', 26, 'suspicious'),
            ('254710123456', 'LOGIN_OTP', 26.2, 'flagged'),
            ('254745777888', 'NEW_DEVICE', 50, 'suspicious'),
            ('254722111222', 'LOGIN', 130, 'safe'),
            ('254733333444', 'PASSWORD_RESET', 3, 'suspicious'),
        ]
        for (msisdn, etype, hours, level) in events:
            db.session.add(AccountEvent(
                msisdn=msisdn, event_type=etype,
                ip_address='41.90.68.10', location='Nairobi',
                device_hash='dev-seed-01',
                details={'source': 'seed'},
                event_datetime=base - timedelta(hours=hours),
                risk_level=level,
                risk_score=65 if level == 'flagged' else (35 if level == 'suspicious' else 5),
                reasons=['PIN + OTP sequence'] if etype == 'LOGIN_OTP'
                        else (['Sensitive account event'] if level == 'suspicious' else []),
                status='open',
            ))
        db.session.commit()

    if Alert.query.count() == 0:
        base = now()
        alerts = [
            ('SIM_SWAP', '254722111222', 'SIM swap FLAGGED',
             'Repeat SIM swap detected on 254722111222 within 2 days of the last swap.',
             'HIGH', 70, 'open', 'SMS'),
            ('AIRTIME_TRANSFER', '254710123456', 'Airtime transfer FLAGGED',
             'A transfer of KES 500 from 254710123456 to a new recipient was flagged.',
             'HIGH', 70, 'open', 'SMS'),
            ('ACCOUNT_TAKEOVER', '254710123456', 'Suspicious account activity',
             'PIN change followed by an OTP attempt within 10 minutes on 254710123456.',
             'CRITICAL', 85, 'acknowledged', 'BOTH'),
            ('SIM_SWAP', '254733333444', 'Suspicious SIM swap detected',
             'SIM swap requested via SIM toolkit channel on 254733333444.',
             'MEDIUM', 45, 'resolved', 'SMS'),
        ]
        for idx, (atype, msisdn, title, msg, sev, score, status, channel) in enumerate(alerts):
            db.session.add(Alert(
                alert_type=atype, msisdn=msisdn, title=title, message=msg,
                severity=sev, risk_score=score, status=status, channel_sent=channel,
                created_at=base - timedelta(hours=idx * 3 + 4),
                resolved_at=(base - timedelta(hours=2)) if status == 'resolved' else None,
            ))
        db.session.commit()

    if NotificationLog.query.count() == 0:
        base = now()
        for i, channel in enumerate(['SMS', 'SMS', 'VOICE', 'SMS']):
            db.session.add(NotificationLog(
                alert_id=i + 1,
                msisdn=['254722111222', '254710123456', '254710123456', '254733333444'][i],
                channel=channel,
                provider='AFRICASTALKING',
                request_payload={'message': 'seed notification'},
                response_payload={'SMSMessageData': {'Message': 'Sent to 1/1'}},
                success=True,
                created_at=base - timedelta(hours=i * 3 + 3),
            ))
        db.session.commit()


def main():
    print('Seeding fraud_detection_db ...')
    with app.app_context():
        db.create_all()
        seed_users()
        seed_rules()
        seed_subscribers()
        seed_events()
    print('Done. Credentials: admin@fraudshield.io / Admin@123'
          '  (analyst@fraudshield.io / Analyst@123)')


if __name__ == '__main__':
    main()
