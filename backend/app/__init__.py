import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


from .models.models import *
from .controllers import version_1 as v1

def create_app():
    """Create a Flask application instance."""
    app = Flask(__name__)
    # DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql:///library-db')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://collins_kipngetich_user:1Ed57ocQHhu63emuds6ps7aYrH5NMGob@dpg-d9nr5a0ae00c73a878ng-a.oregon-postgres.render.com/collins_kipngetich')

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(v1)
    return app