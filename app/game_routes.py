from flask import Blueprint, request, jsonify, abort
import json
from extensions import db
from datetime import datetime
from models import Game
from models import User
from utils import validate_game, determine_game_state, check_winner, game_to_dict, save_game, update_rating

game_bp = Blueprint('game', __name__, url_prefix='/api/v1/games')
user_bp = Blueprint('user', __name__, url_prefix='/api/v1/users')

@game_bp.route('/', methods=['POST'])
def create_game():
    data = request.get_json()
    try:
        is_valid, error = validate_game(data['board'])
        if not is_valid:
            abort(400, description=error)
        game_state = determine_game_state(data['board'])
        game = Game(
            name=data['name'],
            difficulty=data['difficulty'],
            board=data['board'],
            game_state=game_state,
            players=data.get('players', []),
            isLocal=data["local"]
        )
        db.session.add(game)
        db.session.commit()
        return jsonify(game_to_dict(game)), 201
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@game_bp.route('/', methods=['GET'])
def get_all_games():
    difficulty = request.args.get('difficulty')
    name = request.args.get('name')
    modified_since = request.args.get('modified_since')
    query = Game.query
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if name:
        query = query.filter(Game.name.ilike(f"%{name}%"))
    if modified_since:
        try:
            since_date = datetime.strptime(modified_since, "%Y-%m-%d")
            query = query.filter(Game.updated_at >= since_date)
        except ValueError:
            abort(400, description="Invalid date format. Use YYYY-MM-DD.")
    games = query.all()
    return jsonify([game_to_dict(game) for game in games]), 200

@game_bp.route('/get_game_data_by_code/<code>', methods=['GET'])
def get_game_data_by_code(code):
    print("GET GAME DATA BY CODE-------------------")
    game = Game.query.filter_by(code=code).first()
    print(game)
    if not game:
        print("NENÍ HRA")
        abort(404)
    return jsonify(game_to_dict(game)), 200

@game_bp.route('/<uuid>', methods=['GET'])
def get_game(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    return jsonify(game_to_dict(game)), 200

@game_bp.route('/<uuid>', methods=['PUT'])
def update_game(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    data = request.get_json()
    try:
        is_valid, error = validate_game(data['board'])
        if not is_valid:
            abort(400, description=error)
        game.name = data['name']
        game.difficulty = data['difficulty']
        game.board = data['board']
        players = json.loads(game.players) if isinstance(game.players, str) else game.players
        if check_winner(data['board'], "X"):
            game.game_state = 'endgame'
            for player in players:
                if player['role'] == "X":
                    game.winnerId = player['user_id']

        elif check_winner(data['board'], "O"):
            game.game_state = 'endgame'
            for player in players:
                if player['role'] == "O":
                    game.winnerId = player['user_id']
        else:
            game.game_state = determine_game_state(data['board'])
        db.session.commit()
        if game.isLocal:
            save_game(game, players[0]["user_id"])
        else:
            for player in players:
                save_game(game, player["user_id"])

        if game.winnerId is not None and not game.isLocal:
            print("UPDATE RATING")
            if game.winnerId == players[0]['user_id']:
                update_rating(players[1]['user_id'], players[0]['user_id'], "losses")
                update_rating(players[0]['user_id'], players[1]['user_id'], "wins")
            else:
                update_rating(players[0]['user_id'], players[1]['user_id'], "losses")
                update_rating(players[1]['user_id'], players[0]['user_id'], "wins")

        return jsonify(game_to_dict(game)), 200
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@game_bp.route('/<uuid>', methods=['DELETE'])
def delete_game(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    db.session.delete(game)
    db.session.commit()
    return '', 204

@user_bp.route('/', methods=['POST'])
def create_user():
    data = request.get_json()
    try:
        user = User(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            rating=data.get('rating', 1000)
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@user_bp.route('/', methods=['GET'])
def get_all_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@user_bp.route('/<uuid>', methods=['GET'])
def get_user(uuid):
    user = User.query.get(uuid)
    if not user:
        abort(404)
    return jsonify(user.to_dict()), 200

@user_bp.route('/<uuid>', methods=['PUT'])
def edit_user(uuid):
    user = User.query.get(uuid)
    if not user:
        abort(404)
    data = request.get_json()
    try:
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'password' in data:
            user.password = data['password']
        db.session.commit()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        abort(422, description=str(e))

@user_bp.route('/<uuid>', methods=['DELETE'])
def delete_user(uuid):
    user = User.query.get(uuid)
    if not user:
        abort(404)
    db.session.delete(user)
    db.session.commit()
    return '', 204
