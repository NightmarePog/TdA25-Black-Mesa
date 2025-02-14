from flask import Blueprint, request, jsonify, abort
from extensions import db
from models import User
from uuid import uuid4
import hashlib
import json
from datetime import datetime

user_bp = Blueprint('user', __name__, url_prefix='/api/v1/users')

@user_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    try:
        if data.get('loginBy') in ["0", 0]:
            timestamp = int(datetime.now().timestamp())
            data['username'] = f"{data['username']}_{timestamp}"
            if User.query.filter_by(username=data['username']).first():
                abort(400, description="Username already exists")
            player = User(
                username=data['username'],
                login_by=data['loginBy'],
                email=str(uuid4()),
                password_hash="guest"
            )
            db.session.add(player)
            db.session.commit()
            return jsonify({"message": "User registered successfully", "id": player.id, "username": player.username}), 201
        else:
            if not data.get('username') or not data.get('email'):
                abort(400, description="Username and email are required")
            if User.query.filter_by(username=data['username']).first() or User.query.filter_by(email=data['email']).first():
                abort(400, description="Username or email already exists")
            player = User(
                username=data['username'],
                email=data['email'],
                login_by=data['loginBy']
            )
            if data.get('password'):
                player.set_password(data['password'])
            db.session.add(player)
            db.session.commit()
            return jsonify({"message": "User registered successfully", "id": player.id, "username": player.username}), 201
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@user_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    try:
        player = User.query.filter_by(email=data['email']).first()
        if not player:
            abort(404, description="User not found")
        if player.login_by == "1" and not player.check_password(data['password']):
            abort(400, description="Invalid credentials")
        return jsonify({"message": "Login successful", "id": player.id, "username": player.username}), 200
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

@user_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 200

@user_bp.route('/<id>', methods=['GET'])
def get_player(id):
    player = User.query.get(id)
    if not player:
        abort(404)
    return jsonify({
        "id": player.id,
        "username": player.username,
        "email": player.email,
        "loginBy": player.login_by
    }), 200

@user_bp.route('/saved_games/<int:user_id>', methods=['GET'])
def get_saved_games(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    saved_games = json.loads(user.saved_games) if isinstance(user.saved_games, str) else user.saved_games
    return jsonify([{"uuid": k, **v} for k, v in saved_games.items()])

@user_bp.route('/saved_games/<int:user_id>/<game_uuid>', methods=['DELETE'])
def delete_saved_game(user_id, game_uuid):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    saved_games = json.loads(user.saved_games)
    if game_uuid in saved_games:
        del saved_games[game_uuid]
        user.saved_games = json.dumps(saved_games)
        db.session.commit()
        return jsonify({"message": "Game deleted successfully"}), 200
    else:
        return jsonify({"error": "Game not found"}), 404

@user_bp.route('/saved_games/<int:user_id>/<game_uuid>', methods=['GET'])
def get_saved_game(user_id, game_uuid):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    saved_games = json.loads(user.saved_games) if isinstance(user.saved_games, str) else user.saved_games
    return jsonify(saved_games.get(game_uuid, {}))

@user_bp.route('/get_score/<user_id>')
def get_score(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user_stats = {
        'wins': user.wins,
        'draws': user.draws,
        'losses': user.losses,
        'rating': user.rating
    }
    return jsonify(user_stats)

@user_bp.route('/get_users', methods=['GET'])
def get_users():
    users = User.query.all()
    users_list = [{"id": user.id, "username": user.username} for user in users]
    return jsonify(users_list)