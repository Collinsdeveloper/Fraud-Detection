from flask import Flask
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .config import Config

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()


from .models.models import *  # noqa: E402,F401,F403
from .controllers import version_1 as v1  # noqa: E402


def create_app(config_object=None):
    """Create and configure the FraudShield Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    app.register_blueprint(v1, url_prefix='/api/v1')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'fraud-shield'}, 200

    return app
