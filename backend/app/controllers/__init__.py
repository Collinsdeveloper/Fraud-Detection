from flask_restful import Api
from flask import Blueprint

from .auth_controller import AuthView, RegisterOperator, WhoamiView, OperatorListView
from .subscriber_controller import SubscriberList, SubscriberDetail
from .simswap_controller import SimSwapList, SimSwapDetail
from .airtime_controller import AirtimeList, AirtimeDetail
from .account_controller import AccountEventList, AccountEventDetail
from .alert_controller import AlertList, AlertStatus
from .dashboard_controller import DashboardSummary
from .rule_controller import RuleList, RuleDetail
from .simulation_controller import SimulateSimSwap, SimulateAirtime, SimulateAccount
from .notification_controller import TestNotification, NotificationLogList
from .ussd_controller import UssdCallback

version_1 = Blueprint('api_v1', __name__)
api = Api(version_1)

# ---- Authentication & operators ----
api.add_resource(AuthView, '/auth/login')
api.add_resource(WhoamiView, '/auth/me')
api.add_resource(RegisterOperator, '/auth/register')
api.add_resource(OperatorListView, '/operators')

# ---- Subscribers ----
api.add_resource(SubscriberList, '/subscribers')
api.add_resource(SubscriberDetail, '/subscribers/<int:subscriber_id>')

# ---- SIM swap monitoring ----
api.add_resource(SimSwapList, '/sim-swaps', '/sim-swaps/<int:event_id>')
api.add_resource(SimSwapDetail, '/sim-swaps/<int:event_id>/detail')

# ---- Airtime transfer monitoring ----
api.add_resource(AirtimeList, '/airtime/transfers', '/airtime/transfers/<int:event_id>')
api.add_resource(AirtimeDetail, '/airtime/transfers/<int:event_id>/detail')

# ---- Account takeover monitoring ----
api.add_resource(AccountEventList, '/account/events', '/account/events/<int:event_id>')
api.add_resource(AccountEventDetail, '/account/events/<int:event_id>/detail')

# ---- Alerts ----
api.add_resource(AlertList, '/alerts', '/alerts/<int:alert_id>')
api.add_resource(AlertStatus, '/alerts/<int:alert_id>/status')

# ---- Dashboard & rules ----
api.add_resource(DashboardSummary, '/dashboard/summary')
api.add_resource(RuleList, '/rules', '/rules/<int:rule_id>')
api.add_resource(RuleDetail, '/rules/<int:rule_id>/detail')

# ---- Simulation / ingestion playground ----
api.add_resource(SimulateSimSwap, '/simulate/sim-swap')
api.add_resource(SimulateAirtime, '/simulate/airtime')
api.add_resource(SimulateAccount, '/simulate/account')

# ---- Notifications ----
api.add_resource(TestNotification, '/notifications/test')
api.add_resource(NotificationLogList, '/notifications/logs')

# ---- USSD channel (Africa's Talking callback; public by design) ----
api.add_resource(UssdCallback, '/ussd')
