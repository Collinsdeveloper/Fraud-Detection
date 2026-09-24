from flask_bcrypt import Bcrypt
from app import create_app, db
from app.models.models import *

app = create_app()
app.app_context().push()
bcrypt = Bcrypt(app)

class Seed:
    @staticmethod
    def seed_data():
        # Create sample users
        #check if users already exist to avoid duplicate entries

        user_dict1 = {
            'active': 'active',
            'email': 'admin@library.com',
            'password_hash': Bcrypt().generate_password_hash('admin123').decode('utf-8'),
            'role': 'Admin'
        }
        user_dict2 = {
            'active': 'active',
            'email': 'librarian@library.com',
            'password_hash': Bcrypt().generate_password_hash('librarian123').decode('utf-8'),
            'role': 'librarian'
        }
        user_dict3 = {
            'active': 'active',
            'email': 'student1@library.com',
            'password_hash': Bcrypt().generate_password_hash('student123').decode('utf-8'),
            'role': 'student'
        }
        user_dict4 = {
            'active': 'active',
            'email': 'student2@library.com',
            'password_hash': Bcrypt().generate_password_hash('student123').decode('utf-8'),
            'role': 'student'
        }
        user_list = [user_dict1, user_dict2, user_dict3, user_dict4]
        for user_dict in user_list:
            existing_user = User.query.filter_by(email=user_dict['email']).first()
            if existing_user:
                print(f"User with email {user_dict['email']} already exists. Skipping seeding.")
                continue
            user = User(status=user_dict['active'], email=user_dict['email'], password_hash=user_dict['password_hash'], role=user_dict['role'])
            db.session.add(user)
            db.session.commit()

    def seed_user_profiles(self):
        # Create sample user profiles
        user1 = User.query.filter_by(email='admin@library.com').first()
        user2 = User.query.filter_by(email='librarian@library.com').first()
        user3 = User.query.filter_by(email='student1@library.com').first()
        user4 = User.query.filter_by(email='student2@library.com').first()

        # User 1
        if not UserProfile.query.filter_by(user_id=user1.user_id).first():
            profile1 = UserProfile(
                user_id=user1.user_id,
                first_name='Admin',
                last_name='User',
                date_of_birth='1990-01-01',
                address='123 Main St',
                phone_number='1234567890'
            )
            db.session.add(profile1)
        else:
            print(f"Profile for {user1.email} already exists. Skipping.")

        # User 2
        if not UserProfile.query.filter_by(user_id=user2.user_id).first():
            profile2 = UserProfile(
                user_id=user2.user_id,
                first_name='Jane',
                last_name='Smith',
                date_of_birth='1992-02-02',
                address='456 Elm St',
                phone_number='0987654321'
            )
            db.session.add(profile2)
        else:
            print(f"Profile for {user2.email} already exists. Skipping.")

        # User 3
        if not UserProfile.query.filter_by(user_id=user3.user_id).first():
            profile3 = UserProfile(
                user_id=user3.user_id,
                first_name='Janet',
                last_name='Student',
                date_of_birth='1985-03-03',
                address='789 Oak St',
                phone_number='5555555555'
            )
            db.session.add(profile3)
        else:
            print(f"Profile for {user3.email} already exists. Skipping.")

        # User 4
        if not UserProfile.query.filter_by(user_id=user4.user_id).first():
            profile4 = UserProfile(
                user_id=user4.user_id,
                first_name='Alice',
                last_name='Johnson',
                date_of_birth='1995-04-04',
                address='321 Pine St',