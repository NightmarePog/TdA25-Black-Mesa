from extensions import db
import json
from uuid import uuid4
from datetime import datetime
import hashlib

class Game(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    name = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    game_state = db.Column(db.String(20), nullable=False, default='unknown')
    board = db.Column(db.JSON, nullable=False)
    players = db.Column(db.JSON, default=[])  # List of players (ID, username, role)
    started = db.Column(db.Boolean, default=False)
    winnerId = db.Column(db.Integer, nullable=True)
    code = db.Column(db.String(6), nullable=True, unique=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code = self.generate_unique_code()

    def generate_unique_code(self):
        while True:
            code = str(uuid4().hex)[:6].lower()
            existing_game = Game.query.filter_by(code=code).first()
            if not existing_game:
                return code

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    login_by = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=True)
    saved_games = db.Column(db.JSON, default={})

    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode('utf-8')).hexdigest()