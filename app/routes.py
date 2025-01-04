from flask import Blueprint, request, jsonify, abort
from .models import db, Game

bp = Blueprint('games', __name__)

@bp.route('/api/v1/games', methods=['POST'])
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
        return jsonify(game.to_dict()), 201
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@bp.route('/api/v1/games', methods=['GET'])
def get_all_games():
    games = Game.query.all()
    return jsonify([game.to_dict() for game in games]), 200

@bp.route('/api/v1/game/<uuid>', methods=['GET'])
def get_game(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    return jsonify(game.to_dict()), 200

@bp.route('/api/v1/games/<uuid>', methods=['PUT'])
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
        return jsonify(game.to_dict()), 200
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@bp.route('/api/v1/games/<uuid>', methods=['DELETE'])
def delete_game(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    db.session.delete(game)
    db.session.commit()
    return '', 204
