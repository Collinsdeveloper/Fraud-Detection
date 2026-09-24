from flask_restful import Api
from flask import Blueprint

from .user_controller import *
from .book_controller import *

version_1 = Blueprint('api_v1', __name__)
api = Api(version_1)

api.add_resource(UserAuthView, '/auth/user')
api.add_resource(RegisterUser, '/register/user')
api.add_resource(UserView, '/users/<int:user_id>')
api.add_resource(CreateUser, '/create/user')
api.add_resource(EditUser, '/edit/user/<int:user_id>')
api.add_resource(DeleteUser, '/delete/user/<int:user_id>')

api.add_resource(CategoryView, '/categories/<int:category_id>')
api.add_resource(CreateCategory, '/create/category')
api.add_resource(EditCategory, '/edit/category/<int:category_id>')
api.add_resource(DeleteCategory, '/delete/category/<int:category_id>')

api.add_resource(BookView, '/books/<int:book_id>')
api.add_resource(CreateBook, '/create/book')
api.add_resource(EditBook, '/edit/book/<int:book_id>')
api.add_resource(DeleteBook, '/delete/book/<int:book_id>')

api.add_resource(BorrowRecordView, '/borrow_records/<int:record_id>')
api.add_resource(CreateBorrowRecord, '/create/borrow_record')
api.add_resource(EditBorrowRecord, '/edit/borrow_record/<int:record_id>')
api.add_resource(DeleteBorrowRecord, '/delete/borrow_record/<int:record_id>')
