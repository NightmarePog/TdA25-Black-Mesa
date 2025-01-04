from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Game(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    name = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    game_state = db.Column(db.String(20), nullable=False, default='unknown')
    board = db.Column(db.JSON, nullable=False)

# Database initialization
def create_tables():
    with app.app_context():  # Ensure the app context is active
        db.create_all()

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"code": 400, "message": "Bad request: " + str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"code": 404, "message": "Resource not found"}), 404

@app.errorhandler(422)
def unprocessable_entity(error):
    return jsonify({"code": 422, "message": "Semantic error: " + str(error)}), 422

# Routes

## FRONTEND
@app.route('/game', methods=['GET'])
def main_page():
    return "tady bude main page :3"

@app.route('/game/<uuid>', methods=['GET'])
def main_page(uuid):
    return "tady bude hra :3"

## BACKEND

@app.route('/api/v1/games', methods=['POST'])
def create_game():
    data = request.get_json()
    try:
        game = Game(
            name=data['name'],
            difficulty=data['difficulty'],
            board=data['board']
        )
        db.session.add(game)
        db.session.commit()
        return jsonify(game_to_dict(game)), 201
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@app.route('/api/v1/games', methods=['GET'])
def get_all_games():
    games = Game.query.all()
    return jsonify([game_to_dict(game) for game in games]), 200

@app.route('/api/v1/games/<uuid>', methods=['GET'])
def get_game(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    return jsonify(game_to_dict(game)), 200

@app.route('/api/v1/games/<uuid>', methods=['PUT'])
def update_game(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    data = request.get_json()
    try:
        game.name = data['name']
        game.difficulty = data['difficulty']
        game.board = data['board']
        db.session.commit()
        return jsonify(game_to_dict(game)), 200
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@app.route('/api/v1/games/<uuid>', methods=['DELETE'])
def delete_game(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    db.session.delete(game)
    db.session.commit()
    return '', 204

# Helper function
def game_to_dict(game):
    return {
        "uuid": game.uuid,
        "createdAt": game.created_at.isoformat(),
        "updatedAt": game.updated_at.isoformat(),
        "name": game.name,
        "difficulty": game.difficulty,
        "gameState": game.game_state,
        "board": game.board
    }

if __name__ == '__main__':
    create_tables()  # Volání funkce pro vytvoření tabulek
    app.run(debug=True)
