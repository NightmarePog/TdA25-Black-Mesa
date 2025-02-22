from flask import Blueprint, request, jsonify, abort
from extensions import db
from models import User
from uuid import uuid4
import hashlib
import json
from datetime import datetime
import secrets
from utils import user_to_dict

user_bp = Blueprint('user', __name__, url_prefix='/api/v1/users')

@user_bp.route('', methods=['POST'])
def register_user():
    data = request.get_json()
    mes, cd = User.register(data)
    if cd == 201:
        token = User.create_token(mes['uuid'])  # Use 'uuid' instead of 'id'
        response = jsonify(mes)
        response.set_cookie(
            'auth_token',
            value=token,
            httponly=True,
            secure=True,
            samesite='Strict',
        )
        return response, cd
    elif cd == 400 or cd == 422:
        abort(cd, description=mes)
    
@user_bp.route('', methods=['GET'])
def get_all_users():
    query = User.query
    users = query.all()
    return jsonify([user_to_dict(user) for user in users]), 200

@user_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    try:
        player = User.query.filter_by(email=data['email']).first()
        if not player:
            abort(404, description="User not found")
        if player.login_by == "1" and not player.check_password(data['password']):
            abort(400, description="Invalid credentials")

        # Generování tokenu
        new_token = secrets.token_urlsafe(64)
        
        # Aktualizace databáze
        if not player.tokens:
            player.tokens = []
        player.tokens.append(new_token)
        db.session.commit()

        # Vytvoření odpovědi a nastavení cookie
        response = jsonify({
            "message": "Login successful",
            "id": player.uuid,
            "username": player.username
        })
        
        # Nastavení bezpečného cookie
        response.set_cookie(
            'auth_token',
            value=new_token,
            httponly=True,         # Blokuje přístup přes JavaScript
            secure=True,            # Posílá pouze přes HTTPS
            samesite='Strict',     # Ochrana proti CSRF
        )
        
        return response, 200

    except KeyError as e:
        db.session.rollback()
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        db.session.rollback()
        abort(422, description=str(e))

@user_bp.route('/<uuid>', methods=['DELETE'])
def delete_user(uuid):
    user = User.query.get(uuid)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 200

@user_bp.route('/<uuid>', methods=['GET'])
def get_player(uuid):
    player = User.query.get(uuid)
    if not player:
        abort(404)
    return jsonify({
        "id": player.uuid,
        "username": player.username,
        "email": player.email,
        "loginBy": player.login_by,
        "ban": player.ban
    }), 200

@user_bp.route('/saved_games/<string:user_id>', methods=['GET'])
def get_saved_games(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    saved_games = json.loads(user.saved_games) if isinstance(user.saved_games, str) else user.saved_games
    return jsonify([{"uuid": k, **v} for k, v in saved_games.items()])

@user_bp.route('/ban/<string:user_id>', methods=['POST'])
def ban_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user.ban = not user.ban
    db.session.commit()
    mes = "User banned successfully"
    if not user.ban:
        mes = "User unbanned successfully"

    return jsonify({"message": mes}), 200

@user_bp.route('/saved_games/<user_uuid>/<game_uuid>', methods=['DELETE'])
def delete_saved_game(user_uuid, game_uuid):
    user = User.query.get(user_uuid)
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

@user_bp.route('/saved_games/<user_uuid>/<game_uuid>', methods=['GET'])
def get_saved_game(user_uuid, game_uuid):
    user = User.query.get(user_uuid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    saved_games = json.loads(user.saved_games) if isinstance(user.saved_games, str) else user.saved_games
    return jsonify(saved_games.get(game_uuid, {}))

@user_bp.route('/get_score/<user_uuid>', methods=['GET'])
def get_score(user_uuid):
    user = User.query.get(user_uuid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user_stats = {
        'wins': user.wins,
        'draws': user.draws,
        'losses': user.losses,
        'rating': user.elo
    }
    return jsonify(user_stats)

@user_bp.route('/get_users', methods=['POST'])
def get_users():
    '''
    Endpoint pro získání uživatelů v zadaném rozsahu.
    Očekává JSON ve formátu:
    {
        "min": int (výchozí 0),
        "max": int (výchozí poslední index)
    }
    '''
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Získání základních parametrů
        min_users = int(data.get("min", 0))
        max_users_provided = "max" in data
        max_users = int(data["max"]) if max_users_provided else None
    except ValueError:
        return jsonify({"error": "min and max must be integers"}), 400

    # Získání celkového počtu uživatelů
    total_users = User.query.count()
    
    # Automatické nastavení max pro prázdnou databázi
    if total_users == 0:
        return jsonify({"users": [], "count": 0}), 200

    # Nastavení výchozí hodnoty max
    if not max_users_provided:
        max_users = total_users - 1

    # Validace vstupů
    if min_users < 0:
        return jsonify({"error": "min cannot be negative"}), 400
    
    if max_users < min_users:
        return jsonify({"error": "max must be >= min"}), 400

    # Korekce horní hranice
    max_users = min(max_users, total_users - 1)

    # Výpočet limitu pro dotaz
    limit = max_users - min_users + 1

    # Získání uživatelů s řazením podle data vytvoření
    users = User.query.order_by(User.created_at.asc()).offset(min_users).limit(limit).all()

    # Serializace výsledků (bez citlivých údajů)
    users_data = [user_to_dict(user) for user in users]

    return jsonify({
        "users": users_data,
        "count": len(users_data),
        "total": total_users
    })



@user_bp.route('/search', methods=['POST'])
def search_users():
    """
    Endpoint pro vyhledávání uživatelů dle dotazu.
    Očekává JSON ve formátu:
    {
        "query": "část jména"
    }
    """
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "No search query provided"}), 400

    query_str = data['query']
    # Vyhledávání s využitím case-insensitive částečné shody
    users = User.query.filter(User.username.ilike(f"%{query_str}%")) \
                      .order_by(User.created_at.asc()) \
                      .all()
    
    users_by_uuid = User.query.filter(User.uuid.ilike(f"%{query_str}%")) \
                      .order_by(User.created_at.asc()) \
                      .all()
    
    for user in users_by_uuid:
        if user not in users:
            users.append(user)

    users_data = [user_to_dict(user) for user in users]

    return jsonify({
        "users": users_data,
        "count": len(users_data)
    }), 200