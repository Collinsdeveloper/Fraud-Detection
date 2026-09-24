import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://collins-kipngetich@/fraud_detection_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False

    # ---- Africa's Talking (sandbox default) ----
    AT_USERNAME = os.environ.get('AT_USERNAME', 'sandbox')
    AT_API_KEY = os.environ.get('AT_API_KEY', '')
    # Optional. In the sandbox, omit `from` (leave empty) so delivery succeeds.
    AT_SENDER_ID = os.environ.get('AT_SENDER_ID', '')
    AT_VOICE_FROM = os.environ.get('AT_VOICE_FROM', '+254711082000')
    AT_SMS_URL = os.environ.get(
        'AT_SMS_URL', 'https://api.sandbox.africastalking.com/version1/messaging'
    )
    AT_VOICE_URL = os.environ.get(
        'AT_VOICE_URL', 'https://voice.sandbox.africastalking.com/call'
    )
    # Sandbox voice often has no reachable host; simulate so the pipeline is demoable.
    AT_SIMULATE_VOICE_ON_UNAVAILABLE = os.environ.get(
        'AT_SIMULATE_VOICE_ON_UNAVAILABLE', 'true'
    ).lower() in ('true', '1', 'yes')

    # ---- App behaviour ----
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))
    COUNTRY_CODE = os.environ.get('COUNTRY_CODE', '254')
    # Alerts at or above this severity trigger outbound notifications
    DEFAULT_NOTIFY_LEVEL = os.environ.get('DEFAULT_NOTIFY_LEVEL', 'HIGH')
