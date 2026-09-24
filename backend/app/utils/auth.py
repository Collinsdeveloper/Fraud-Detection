from datetime import datetime, timedelta

import jwt
from flask import request, current_app

from ..models.models import User

JWT_ALGORITHM = 'HS256'


def now_utc():
    return datetime.utcnow()


def encode_token(user, ttl_hours=None):
    """Create a signed JWT for a logged-in operator."""
    ttl = ttl_hours or current_app.config.get('JWT_EXPIRATION_HOURS', 24)
    payload = {
        'user_id': user.user_id,
        'email': user.email,
        'role': user.role,
        'iat': now_utc(),
        'exp': now_utc() + timedelta(hours=ttl),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Return the decoded payload or raise jwt exceptions."""
    return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=[JWT_ALGORITHM])


def _extract_identity():
    """Parse + validate the Authorization header. Returns (identity, error)."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, ({'message': 'Missing or malformed Authorization header'}, 401)
    token = auth_header.split(' ', 1)[1].strip()
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        return None, ({'message': 'Session expired. Please log in again.'}, 401)
    except jwt.InvalidTokenError:
        return None, ({'message': 'Invalid authentication token'}, 401)

    user = User.query.get(payload.get('user_id'))
    if not user:
        return None, ({'message': 'Account no longer exists'}, 401)
    if user.status != 'active':
        return None, ({'message': 'Account disabled. Contact an administrator.'}, 403)
    return {'user_id': user.user_id, 'email': user.email, 'role': user.role}, None


def current_identity():
    """Return the authenticated identity dict or None (no error response)."""
    identity, _ = _extract_identity()
    return identity


def staff_identity():
    """Guard used at the top of protected handlers.

    Returns (identity, None) on success or (None, (json, status_code)) so the
    caller can simply do `return error` when the call fails.
    """
    identity, error = _extract_identity()
    if error:
        return None, error
    return identity, None


def admin_identity():
    """Guard for admin-only handlers. Same contract as staff_identity."""
    identity, error = _extract_identity()
    if error:
        return None, error
    if identity['role'] != 'admin':
        return None, ({'message': 'Admin privileges required'}, 403)
    return identity, None
