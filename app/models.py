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
    isRanked = db.Column(db.Boolean, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code = self.generate_unique_code()

    def generate_unique_code(self):
        while True:
            code = str(uuid4().int)[:6].lower()
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
    elo = db.Column(db.Integer, default=400)
    ban = db.Column(db.Boolean, default=False)
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
    
    # models.py - User class
    @staticmethod
    def register(data):
        try:
            # Povinné pole loginBy
            if 'loginBy' not in data:
                data['loginBy'] = "1"
            
            login_by = str(data['loginBy'])

            # Guest registrace (loginBy=0)
            if login_by == "0":
                # Generování unikátního uživatelského jména
                timestamp = int(datetime.now().timestamp())
                base_username = data.get('username', 'Guest')
                username = f"{base_username}_{timestamp}"
                
                # Kontrola unikátnosti
                while User.query.filter_by(username=username).first():
                    timestamp += 1
                    username = f"{base_username}_{timestamp}"

                player = User(
                    username=username,
                    email=f"{uuid4()}@guest.local",  # Generovaný email
                    login_by=login_by,
                    elo=data.get('elo', 400),       # Výchozí ELO 400
                    password_hash="guest"            # Speciální hodnota pro hosty
                )

            # Plná registrace (loginBy=1)
            elif login_by == "1":
                # Validace povinných polí dle API spec
                required_fields = ['username', 'email', 'password']
                for field in required_fields:
                    if field not in data:
                        return f"Missing field: {field}", 400

                # Kontrola duplicit
                if User.query.filter_by(username=data['username']).first():
                    return "Username already exists", 400
                if User.query.filter_by(email=data['email']).first():
                    return "Email already exists", 400

                player = User(
                    username=data['username'],
                    email=data['email'],
                    login_by=login_by,
                    elo=data.get('elo', 400)
                )
                player.set_password(data['password'])

            else:
                return "Invalid loginBy value", 400

            db.session.add(player)
            db.session.commit()

            # Response podle API specifikace
            return {
                "uuid": player.uuid,
                "createdAt": player.created_at.isoformat(),
                "username": player.username,
                "email": player.email,
                "elo": player.elo,
                "wins": player.wins,
                "draws": player.draws,
                "losses": player.losses
            }, 201

        except Exception as e:
            db.session.rollback()
            return str(e), 422