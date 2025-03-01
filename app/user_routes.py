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


from flask import make_response

@user_bp.route('/logout', methods=['GET'])
def logout():
    response = make_response("Odhlášeno")
    response.set_cookie(
        'auth_token',
        value='',  # Prázdná hodnota
        expires=0,  # Expirace v minulosti
        httponly=True,
        secure=True,
        samesite='Strict'
    )
    return response

    
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
            "uuid": player.uuid,
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
    
    if user.email == "tda@scg.cz":
        return jsonify({"error": "You cannot delete the admin"}), 400
    
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

@user_bp.route('/isAdmin', methods=['GET'])
def isAdminByCookies():
    auth_token = request.cookies.get('auth_token')
    if not auth_token:
        return jsonify({"error": "No token provided"}), 401

    # Přetypování JSON sloupce na text a hledání tokenu jako podřetězce
    user = User.query.filter(User.tokens.cast(db.Text).like(f'%"{auth_token}"%')).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.email == "tda@scg.cz":
        return jsonify({"isAdmin": True}), 200
    else:
        return jsonify({"isAdmin": False}), 200



@user_bp.route('/ban/<string:user_id>', methods=['POST'])
def ban_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.email == "tda@scg.cz":
        return jsonify({"error": "You cannot ban the admin"}), 400
    
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

@user_bp.route('/getBannedUsers', methods=['GET'])
def get_banned_users():
    banned_users = User.query.filter_by(ban=True).all()
    return jsonify([user_to_dict(user) for user in banned_users]), 200

@user_bp.route('/get_users', methods=['POST'])
def get_users():
    '''
    Endpoint pro získání všech uživatelů seřazených od nejvyššího ELO
    '''
    # Získání všech uživatelů seřazených podle ELO
    users = User.query.order_by(User.elo.desc()).all()
    
    # Debug výpis pro kontrolu
    print("Všechny uživatelské ELO:")
    for user in users:
        print(f"{user.username}: {user.elo} (ID: {user.uuid})")
    
    # Serializace výsledků
    users_data = [user_to_dict(user) for user in users]
    
    return jsonify({
        "users": users_data,
        "count": len(users_data),
        "total": len(users_data)
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