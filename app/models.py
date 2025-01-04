from datetime import datetime
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Game(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    name = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    game_state = db.Column(db.String(20), nullable=False, default='unknown')
    board = db.Column(db.JSON, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "name": self.name,
            "difficulty": self.difficulty,
            "gameState": self.game_state,
            "board": self.board
        }
