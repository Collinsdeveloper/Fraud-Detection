from flask_restful import Resource, request

from app import db
from ..models.models import FraudRule
from ..schemas.schemas import FraudRuleSchema
from ..utils.auth import admin_identity


class RuleList(Resource):
    """GET/POST /rules"""

    def get(self, rule_id=0):
        identity, error = admin_identity()
        if error:
            return error
        if rule_id:
            rule = FraudRule.query.get(rule_id)
            if not rule:
                return {'message': 'Rule not found'}, 404
            return FraudRuleSchema.dump(rule), 200
        rules = FraudRule.query.order_by(FraudRule.category, FraudRule.rule_id).all()
        return {'items': [FraudRuleSchema.dump(r) for r in rules]}, 200

    def post(self):
        identity, error = admin_identity()
        if error:
            return error
        data = request.get_json(force=True) or {}
        name = (data.get('name') or '').strip()
        code = (data.get('code') or '').strip().upper()
        if not name or not code:
            return {'message': 'name and code are required'}, 400
        if FraudRule.query.filter_by(code=code).first():
            return {'message': f'A rule with code {code} already exists'}, 400

        rule = FraudRule(
            name=name,
            code=code,
            description=data.get('description'),
            category=(data.get('category') or 'GLOBAL').upper(),
            weight=int(data.get('weight', 20)),
            severity=(data.get('severity') or 'MEDIUM').upper(),
            is_active=bool(data.get('is_active', True)),
            config=data.get('config') or {},
        )
        db.session.add(rule)
        db.session.commit()
        return FraudRuleSchema.dump(rule), 201


class RuleDetail(Resource):
    """GET/PUT /rules/<int:rule_id>"""

    def get(self, rule_id):
        identity, error = admin_identity()
        if error:
            return error
        rule = FraudRule.query.get(rule_id)
        if not rule:
            return {'message': 'Rule not found'}, 404
        return FraudRuleSchema.dump(rule), 200

    def put(self, rule_id):
        identity, error = admin_identity()
        if error:
            return error
        rule = FraudRule.query.get(rule_id)
        if not rule:
            return {'message': 'Rule not found'}, 404
        data = request.get_json(force=True) or {}

        if data.get('name'):
            rule.name = data['name'].strip()
        if data.get('description') is not None:
            rule.description = data['description']
        if data.get('category'):
            rule.category = data['category'].upper()
        if 'weight' in data:
            try:
                rule.weight = max(0, min(int(data['weight']), 100))
            except (TypeError, ValueError):
                return {'message': 'weight must be an integer between 0 and 100'}, 400
        if data.get('severity'):
            rule.severity = data['severity'].upper()
        if 'is_active' in data:
            rule.is_active = bool(data['is_active'])
        if data.get('config') is not None:
            existing = rule.config or {}
            existing.update(data['config'])
            rule.config = existing

        db.session.add(rule)
        db.session.commit()
        return FraudRuleSchema.dump(rule), 200
