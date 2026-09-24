"""Africa's Talking REST client (sandbox-ready SMS + Voice).

Reference (OpenAPI):
  SMS   POST {host}/version1/messaging   username, to, message [, from]
  Voice POST {host}/call                 username, from, to [, clientRequestId]

All calls are made non-interactively and parsed into a lightweight dict so the
rest of the app never has to know about HTTP details.
"""
import json

import requests
from flask import current_app


class AfricasTalkingClient:
    SMS_ACCEPTED = (200, 201)

    @staticmethod
    def api_key():
        return current_app.config.get('AT_API_KEY', '')

    @staticmethod
    def configured():
        """We can only truly deliver when an API key is present."""
        return bool(AfricasTalkingClient.api_key())

    @staticmethod
    def _headers():
        return {
            'apiKey': AfricasTalkingClient.api_key(),
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

    @staticmethod
    def send_sms(to, message, sender_id=None):
        """Send an SMS. `to` may contain one or multiple comma separated MSISDNs."""
        url = current_app.config['AT_SMS_URL']
        data = {
            'username': current_app.config['AT_USERNAME'],
            'to': to,
            'message': message,
        }
        if sender_id:
            data['from'] = sender_id
        try:
            resp = requests.post(url, headers=AfricasTalkingClient._headers(),
                                 data=data, timeout=20)
            body = AfricasTalkingClient._parse_body(resp)
            accepted = resp.status_code in AfricasTalkingClient.SMS_ACCEPTED
            api_message = ((body or {}).get('SMSMessageData') or {}).get('Message', '')
            success = accepted and 'SenderId' not in str(api_message)
            return {
                'success': success,
                'status_code': resp.status_code,
                'request': {'to': to, 'from': sender_id, 'message': message[:160]},
                'response': body,
            }
        except requests.RequestException as exc:
            return {
                'success': False,
                'error': str(exc),
                'request': {'to': to, 'from': sender_id, 'message': message[:160]},
                'response': None,
            }

    @staticmethod
    def make_call(to, client_request_id=None, from_number=None):
        """Initiate an outbound voice call (used for voice alerts)."""
        url = current_app.config['AT_VOICE_URL']
        data = {
            'username': current_app.config['AT_USERNAME'],
            'to': to,
            'from': from_number or current_app.config['AT_VOICE_FROM'],
        }
        if client_request_id:
            data['clientRequestId'] = client_request_id
        try:
            resp = requests.post(url, headers=AfricasTalkingClient._headers(),
                                 data=data, timeout=20)
            body = AfricasTalkingClient._parse_body(resp)
            return {
                'success': resp.status_code == 200 or resp.status_code == 201,
                'status_code': resp.status_code,
                'request': {'to': to, 'from': data['from']},
                'response': body,
            }
        except requests.RequestException as exc:
            return {
                'success': False,
                'error': str(exc),
                'request': {'to': to, 'from': data.get('from')},
                'response': None,
            }

    @staticmethod
    def _parse_body(resp):
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {'raw': resp.text[:500] if resp.text else None}
