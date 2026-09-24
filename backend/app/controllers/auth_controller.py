from flask_restful import Resource, request

from app import bcrypt, db
from ..models.models import User
from ..schemas.schemas import UserSchema
from ..utils.auth import admin_identity, encode_token


class AuthView(Resource):
    """POST /auth/login"""

    def post(self):
        data = request.get_json(force=True) or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password')
        if not email or not password:
            return {'message': 'Email and password are required'}, 400

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            return {'message': 'Invalid email or password'}, 401
        if user.status != 'active':
            return {'message': 'Account is disabled. Contact an administrator.'}, 403

        token = encode_token(user)
        return {'token': token, 'user': UserSchema.dump(user)}, 200


class WhoamiView(Resource):
    """GET /auth/me"""

    def get(self):
        from ..utils.auth import current_identity
        identity = current_identity()
        if not identity:
            return {'message': 'Unauthenticated'}, 401
        user = User.query.get(identity['user_id'])
        return UserSchema.dump(user) if user else {'message': 'User not found'}, 200


class RegisterOperator(Resource):
    """POST /auth/register (admin only)"""

    def post(self):
        identity, error = admin_identity()
        if error:
            return error

        data = request.get_json(force=True) or {}
        full_name = (data.get('full_name') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password')
        role = (data.get('role') or 'analyst').lower()
        phone_number = (data.get('phone_number') or '').strip()

        if not full_name or not email or not password:
            return {'message': 'full_name, email and password are required'}, 400
        if role not in ('admin', 'analyst'):
            return {'message': 'role must be admin or analyst'}, 400
        if User.query.filter_by(email=email).first():
            return {'message': 'A user with this email already exists'}, 400

        user = User(
            full_name=full_name,
            email=email,
            phone_number=phone_number or None,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            role=role,
            status='active',
        )
        db.session.add(user)
        db.session.commit()
        return UserSchema.dump(user), 201


class OperatorListView(Resource):
    """GET /operators (admin)"""

    def get(self):
        identity, error = admin_identity()
        if error:
            return error
        users = User.query.order_by(User.created_at.desc()).all()
        return {'items': [UserSchema.dump(u) for u in users]}, 200
