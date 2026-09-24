lass UserSchema:
    @staticmethod
    def dump(user):
        return {
            'user_id': user.user_id,
            'status': user.status,
            'email': user.email,
            'role': user.role,
            'name': f"{user.profile.first_name} {user.profile.last_name}" if user.profile else None,
        }

class UserProfileSchema:
    @staticmethod
    def dump(user_profile):
        return {
            'profile_id': user_profile.profile_id,
            'user_id': user_profile.user_id,
            'first_name': user_profile.first_name,
            'last_name': user_profile.last_name,
            'date_of_birth': user_profile.date_of_birth.isoformat(),
            'address': user_profile.address,
            'phone_number': user_profile.phone_number,
        } 

class CategorySchema:
    @staticmethod
    def dump(category):
        return {
            'category_id': category.category_id,
            'name': category.name,
            'description': category.description,
        }

class BookSchema:
    @staticmethod
    def dump(book):
        return {
            'book_id': book.book_id,
            'title': book.title,
            'author': book.author,
            'publication_year': book.publication_year,
            'category_id': book.category_id,
            'category_name': book.category.name if book.category else None,
        }

class BorrowRecordSchema:
    @staticmethod
    def dump(borrow_record):
        return {