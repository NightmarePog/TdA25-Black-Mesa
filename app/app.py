from flask import Flask, jsonify
from extensions import db, socketio
from models import Game, User
from user_routes import user_bp
from game_routes import game_bp
from frontend_routes import frontend_bp
from socket_handlers import register_socket_handlers
from utils import handle_errors

def create_app():
    app = Flask(__name__, template_folder="frontend")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'your_secret_key_here'

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app)

    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(frontend_bp)

    # Register error handlers
    handle_errors(app)

    # Register socket handlers
    register_socket_handlers(socketio)

    # Create database tables
    with app.app_context():
        db.create_all()
        print("Database initialized")

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True)