from flask import Blueprint, request, jsonify, abort
import json
from extensions import db
from datetime import datetime
from models import Game
from models import User
from utils import validate_game, determine_game_state, check_winner, game_to_dict, save_game, update_rating, user_to_dict
import time
import threading

game_bp = Blueprint('game', __name__, url_prefix='/api/v1/games')

def create_game(data):
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
            isLocal=data["local"],
            isRanked=data.get("ranked", False),
        )
        db.session.add(game)
        db.session.commit()
        return game_to_dict(game), 201, False
    except KeyError as e:
        print(e)
        return f"Missing field: {str(e)}", 400, True
    except Exception as e:
        print(e)
        return str(e), 422, True

@game_bp.route('/', methods=['POST'])
def create_game_api():
    data = request.get_json()
    isUserBanned = User.query.get(data['own']).ban
    if isUserBanned:
        print("User is banned")
        abort(403, description="You are banned")
    
    mes, code, abo = create_game(data)
    if abo:
        abort(code, description=mes)
    return jsonify(mes), code

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
            '''
        if game.winnerId is not None and not game.isLocal:
            print("UPDATE RATING")
            if game.winnerId == players[0]['user_id']:
                update_rating(players[1]['user_id'], players[0]['user_id'], "losses")
                update_rating(players[0]['user_id'], players[1]['user_id'], "wins")
            else:
                update_rating(players[0]['user_id'], players[1]['user_id'], "losses")
                update_rating(players[1]['user_id'], players[0]['user_id'], "wins")
            '''
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

@game_bp.route('/<uuid>/surrender', methods=['PUT'])
def surrender(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
        game.game_state = "draw"
        db.session.commit()
        players = json.loads(game.players) if isinstance(game.players, str) else game.players
        update_rating(players[1]['user_id'], players[0]['user_id'], "draws")
        update_rating(players[0]['user_id'], players[1]['user_id'], "draws")


waitingForGame = {"waiting": {}, "game": {}}
waitingForGameRANKED = {"waiting": {}, "game": {}}

@game_bp.route('/findgame', methods=['POST'])
def findgame_post():  # Renamed function
    data = request.get_json()
    print(data)
    print(data["userId"])
    user = User.query.get(data["userId"])
    if data["ranked"] == "true" or data["ranked"] == True:
        waitingForGameRANKED["waiting"][data["userId"]] = user_to_dict(user)
        if data["userId"] in waitingForGameRANKED["waiting"]:
            return jsonify(waitingForGameRANKED["waiting"][data["userId"]]), 200
        else:
            return jsonify({}), 404
    else:
        waitingForGame["waiting"][data["userId"]] = user_to_dict(user)
        if data["userId"] in waitingForGame["waiting"]:
            return jsonify(waitingForGame["waiting"][data["userId"]]), 200
        else:
            return jsonify({}), 404


@game_bp.route('/findgame', methods=['DELETE'])
def findgame_delete():  # Renamed function
    data = request.get_json()
    if data["userId"] in waitingForGame["waiting"]:
        del waitingForGame["waiting"][data["userId"]]

    elif data["userId"] in waitingForGameRANKED["waiting"]:
        del waitingForGameRANKED["waiting"][data["userId"]]

    return jsonify({}), 200


@game_bp.route('/check-match/<userUuid>', methods=['GET'])
def findgame_get(userUuid):  # Renamed function

    if waitingForGame["game"].get(userUuid):
        gameuuid = waitingForGame["game"].get(userUuid)
        print("CASUAL  GAMEGE")
        waitingForGame["game"].pop(userUuid)
        return jsonify({"gameUuid": gameuuid}), 200
    
    elif waitingForGameRANKED["game"].get(userUuid):
        print("RANKED GAMEGAMEGAMEGAMEGAMEGAMEGAMEGAME")
        gameuuid = waitingForGameRANKED["game"].get(userUuid)
        waitingForGameRANKED["game"].pop(userUuid)
        return jsonify({"gameUuid": gameuuid}), 200
    return jsonify({}), 200

def matchmaking_background_task(app):
    """Párování hráčů v pozadí podle ELO"""
    print("Spouštím matchmaking...")
    while True:
        with app.app_context():
            def casual():
                
                # Získání a seřazení čekajících hráčů
                waiting_players = list(waitingForGame["waiting"].values())
                sorted_players = sorted(waiting_players, key=lambda x: x["elo"])
                
                for player in sorted_players:
                    print(f"{player['username']} (ELO: {player['elo']})")

                # Párování hráčů po dvou
                while len(sorted_players) >= 2:
                    player1 = sorted_players.pop(0)
                    player2 = sorted_players.pop(0)
                    
                    mes, code, abo = create_game({
                        "name": f"{player1['username']} vs {player2['username']}",
                        "difficulty": "medium",
                        "board": [[ "" for _ in range(15)] for _ in range(15)],
                        "players": [],
                        "local": False,
                        "ranked": False
                    })

                    if code == 201:
                        print(mes)
                        waitingForGame["game"][player1["uuid"]] = mes["uuid"]
                        waitingForGame["game"][player2["uuid"]] = mes["uuid"]
                        # Odstranění z čekací fronty
                        del waitingForGame["waiting"][player1["uuid"]]
                        del waitingForGame["waiting"][player2["uuid"]]
                        
                        print(f"Vytvořen zápas mezi: {player1['username']} vs {player2['username']}")
                    else:
                        print(f"Chyba při vytváření hry: {mes}")

            def ranked():
                
                # Získání a seřazení čekajících hráčů
                waiting_players = list(waitingForGameRANKED["waiting"].values())
                sorted_players = sorted(waiting_players, key=lambda x: x["elo"])
                
                for player in sorted_players:
                    print(f"{player['username']} (ELO: {player['elo']})")

                # Párování hráčů po dvou
                while len(sorted_players) >= 2:
                    player1 = sorted_players.pop(0)
                    player2 = sorted_players.pop(0)
                    
                    mes, code, abo = create_game({
                        "name": f"{player1['username']} vs {player2['username']}",
                        "difficulty": "medium",
                        "board": [[ "" for _ in range(15)] for _ in range(15)],
                        "players": [],
                        "local": False,
                        "ranked": True
                    })

                    if code == 201:
                        print(mes)
                        waitingForGameRANKED["game"][player1["uuid"]] = mes["uuid"]
                        waitingForGameRANKED["game"][player2["uuid"]] = mes["uuid"]
                        # Odstranění z čekací fronty
                        del waitingForGameRANKED["waiting"][player1["uuid"]]
                        del waitingForGameRANKED["waiting"][player2["uuid"]]
                        
                        print(f"Vytvořen RANKED zápas mezi: {player1['username']} vs {player2['username']}")
                    else:
                        print(f"Chyba při vytváření RANKED hry: {mes}")

            casual()
            ranked()
            time.sleep(5)