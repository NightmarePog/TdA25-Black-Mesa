from extensions import db
import json
from uuid import uuid4
from datetime import datetime
import hashlib
import secrets

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
    isLocal = db.Column(db.Boolean, default=False)

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
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    login_by = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=True)
    saved_games = db.Column(db.JSON, default={})
    tokens = db.Column(db.JSON, default=[])
    wins = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    elo = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def create_token(user_uuid):
        user = User.query.filter_by(uuid=user_uuid).first()
        # Generování tokenu
        new_token = secrets.token_urlsafe(64)
        
        # Aktualizace databáze
        if not user.tokens:
            user.tokens = []
        user.tokens.append(new_token)
        db.session.commit()
        return new_token
    
    def register(data):
        try:
            if data.get('loginBy') in ["0", 0]:
                timestamp = int(datetime.now().timestamp())
                data['username'] = f"{data['username']}_{timestamp}"
                if User.query.filter_by(username=data['username']).first():
                    return "Username already exists", 400
                player = User(
                    username=data['username'],
                    login_by=data['loginBy'],
                    email=str(uuid4()),
                    password_hash="guest"
                )
                db.session.add(player)
                db.session.commit()
                return {"message": "User registered successfully", "id": player.uuid, "username": player.username}, 201
            else:
                if not data.get('username') or not data.get('email'):
                    return "Username and email are required", 400
                
                if User.query.filter_by(username=data['username']).first() or User.query.filter_by(email=data['email']).first():
                    return "Username or email already exists", 400
                player = User(
                    username=data['username'],
                    email=data['email'],
                    login_by=data['loginBy']
                )
                if data.get('password'):
                    player.set_password(data['password'])
                db.session.add(player)
                db.session.commit()
                
                return {"message": "User registered successfully", "id": player.uuid, "username": player.username}, 201
        except KeyError as e:
            return f"Missing field: {str(e)}", 400
        except Exception as e:
            return str(e), 422