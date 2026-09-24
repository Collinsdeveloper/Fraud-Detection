from flask_restful import Resource, request
from ..models.models import *
from ..schemas.schemas import CategorySchema, BookSchema, BorrowRecordSchema
from .user_controller import current_identity, staff_identity
from datetime import datetime


def paginate(query, serializer):
    """Return a bounded, metadata-rich page from a SQLAlchemy query."""
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    per_page = min(max(request.args.get('per_page', 10, type=int) or 10, 10), 100)
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'items': [serializer(item) for item in result.items],
        'pagination': {
            'page': result.page,
            'per_page': result.per_page,
            'total': result.total,
            'pages': result.pages,
            'has_next': result.has_next,
            'has_prev': result.has_prev,
        }
    }

class CategoryView(Resource):
    def get(self, category_id):
        if category_id == 0:
            categories = Category.query.order_by(Category.category_id)
            return paginate(categories, CategorySchema.dump), 200
        category = Category.query.get(category_id)
        if not category:
            return {'message': 'Category not found'}, 404
        return CategorySchema.dump(category), 200

class CreateCategory(Resource):
    def post(self):
        _, error = staff_identity()
        if error:
            return error
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')

        if not name:
            return {'message': 'Missing required field: name'}, 400

        existing_category = Category.query.filter_by(name=name).first()
        if existing_category:
            return {'message': 'Category with this name already exists'}, 400

        new_category = Category(name=name, description=description)
        db.session.add(new_category)
        db.session.commit()

        return CategorySchema.dump(new_category), 201