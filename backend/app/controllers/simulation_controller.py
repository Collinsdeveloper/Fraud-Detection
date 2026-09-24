from datetime import datetime, timedelta
from random import choice as pick, randint, uniform

from flask_restful import Resource, request

from app import db
from ..models.models import SimSwapEvent, Subscriber
from ..utils.auth import staff_identity
from .airtime_controller import ingest_airtime
from .account_controller import ingest_account
from .simswap_controller import ingest_sim_swap


# Stable fixtures keep the demo deterministic for suspicious/flagged scenarios.
# Normal fixtures are intentionally fresh per request so repeated demo clicks do
# not accumulate history and incorrectly turn a normal case into a risk alert.
_SCENARIO_NUMBERS = {
    'suspicious': '254729999000',
    'flagged': '254710123456',
}


def _fresh_number():
    """Return a synthetic MSISDN not present in the local watch/history tables."""
    while True:
        msisdn = f'2547{randint(0, 99999999):08d}'
        if not Subscriber.query.filter_by(msisdn=msisdn).first() and not SimSwapEvent.query.filter_by(msisdn=msisdn).first():
            return msisdn


def _business_time():
    """Return a daytime UTC timestamp, never during the off-hours rule window."""
    now = datetime.utcnow()
    daytime = now.replace(hour=12, minute=0, second=0, microsecond=0)
    return daytime if daytime <= now else daytime - timedelta(days=1)


def _subscriber_numbers(limit=10):
    subs = db.session.execute(
        db.select(SimSwapEvent.msisdn).distinct().limit(limit)
    ).scalars().all()
    if not subs:
        subs = ['254712345678', '254733456789', '254701234567']
    return list(subs)


def _iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def _sim_swap_payload(scenario='normal'):
    numbers = _subscriber_numbers()
    phones = ['Samsung Galaxy S24', 'Tecno Spark 20', 'iPhone 15', 'Redmi Note 13']
    agents = ['Peter O.', 'Faith N.', 'Mark K.', 'HR Contact Center']
    msisdn = _fresh_number() if scenario == 'normal' else (_SCENARIO_NUMBERS.get(scenario) or pick(numbers))
    base = {
        'msisdn': msisdn,
        'device_model': pick(phones),
        'channel': pick(['WEB', 'RETAILER', 'APP']),
        'agent_name': None,
        'old_imsi': '639021234567890',
        'new_imsi': '639021234567891',
        'old_iccid': '8963911234567890123',
        'new_iccid': '8963911234567890999',
        'swap_datetime': _iso(_business_time()),
    }
    if scenario == 'suspicious':
        base.update({'channel': pick(['AGENT', 'SIM_TOOLKIT', 'WHATSAPP'])})
    elif scenario == 'flagged':
        base.update({
            'channel': 'AGENT',
            'agent_name': pick(agents),
            'new_imsi': '639031234567897',
            'swap_datetime': _iso(datetime.utcnow() - timedelta(minutes=randint(1, 8))),
        })
    return base


def _airtime_payload(scenario='normal'):
    numbers = _subscriber_numbers()
    base = {
        'sender_msisdn': _fresh_number() if scenario == 'normal' else (_SCENARIO_NUMBERS.get(scenario) or pick(numbers)),
        'recipient_msisdn': '254712345679',
        'amount': uniform(20, 400),
        'is_new_recipient': False,
        'method': pick(['USSD', 'APP', 'DIAL_CODE', 'VENDOR']),
        'transfer_datetime': _iso(_business_time()),
    }
    if scenario == 'suspicious':
        base.update({'amount': uniform(600, 900), 'is_new_recipient': True})
    elif scenario == 'flagged':
        base.update({
            'amount': uniform(1500, 5000),
            'is_new_recipient': True,
            'method': 'DIAL_CODE',
        })
    return base


def _account_payload(scenario='normal'):
    numbers = _subscriber_numbers()
    base = {
        'msisdn': _fresh_number() if scenario == 'normal' else (_SCENARIO_NUMBERS.get(scenario) or pick(numbers)),
        'event_type': 'LOGIN',
        'ip_address': f'41.{randint(0, 255)}.{randint(0, 255)}.{randint(0, 255)}',
        'device_hash': 'dev-%08x' % randint(0, 0xFFFFFFFF),
        'location': pick(['Nairobi', 'Mombasa', 'Kisumu', 'Eldoret', 'Nakuru']),
        'event_datetime': _iso(datetime.utcnow() - timedelta(minutes=randint(1, 15))),
    }
    if scenario == 'suspicious':
        base.update({'event_type': pick(['NEW_DEVICE', 'PASSWORD_RESET', 'PROFILE_CHANGE'])})
    elif scenario == 'flagged':
        base.update({
            'event_type': 'OTP_REQUEST',
            'details': {'otp_channel': 'APP', 'attempt': randint(3, 7)},
        })
    return base


def _run(make, ingest, scenario):
    """Generate a payload, ingest it and return the response (dict, list)."""
    payload = make(scenario)
    response, status = ingest(payload)
    return response, status


class SimulateSimSwap(Resource):
    """POST /simulate/sim-swap  {scenario: normal|suspicious|flagged}"""

    def post(self):
        identity, error = staff_identity()
        if error:
            return error
        data = request.get_json(force=True) or {}
        scenario = data.get('scenario', 'normal')
        if scenario not in ('normal', 'suspicious', 'flagged'):
            return {'message': 'scenario must be normal, suspicious or flagged'}, 400
        return _run(_sim_swap_payload, ingest_sim_swap, scenario)


class SimulateAirtime(Resource):
    """POST /simulate/airtime  {scenario: normal|suspicious|flagged}"""

    def post(self):
        identity, error = staff_identity()
        if error:
            return error
        data = request.get_json(force=True) or {}
        scenario = data.get('scenario', 'normal')
        if scenario not in ('normal', 'suspicious', 'flagged'):
            return {'message': 'scenario must be normal, suspicious or flagged'}, 400
        return _run(_airtime_payload, ingest_airtime, scenario)


class SimulateAccount(Resource):
    """POST /simulate/account  {scenario: normal|suspicious|flagged}"""

    def post(self):
        identity, error = staff_identity()
        if error:
            return error
        data = request.get_json(force=True) or {}
        scenario = data.get('scenario', 'normal')
        if scenario not in ('normal', 'suspicious', 'flagged'):
            return {'message': 'scenario must be normal, suspicious or flagged'}, 400
        return _run(_account_payload, ingest_account, scenario)

