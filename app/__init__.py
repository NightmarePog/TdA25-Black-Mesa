from flask import Flask
from .config import Config
from .models import db
from .routes import bp
from .helpers import create_tables

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializace databáze
    db.init_app(app)

    # Registrace blueprintu pro routy
    app.register_blueprint(bp)

    # Vytvoření tabulek při spuštění
    with app.app_context():
        create_tables()

    return app
