from extensions import db, socketio, join_room, emit
from flask import request
from models import Game, User
import json
from utils import check_winner, game_to_dict, save_game, call_delete_game_api, call_update_game_api, determine_game_state, update_rating
import requests, random, threading

turn_timers = {}

def handle_join_game(data):
    game = Game.query.filter_by(uuid=data['game_uuid']).first()
    if not game:
        emit('error', {'message': 'Game not found.'}, room=request.sid)
        return
    
    if User.query.get(data['user_id']).ban:
        emit('error', {'message': 'You are banned.'}, room=request.sid)
        return
    
    if game.isRanked and str(User.query.get(data['user_id']).login_by) == "0":
        emit('error', {'message': 'This game is for registered players only'}, room=request.sid)
        return
    
    players_list = json.loads(game.players) if game.players else []
    
    try:
        # Připoj hráče do místnosti NEŽ začneš emitovat události
        join_room(data['game_uuid'])
        print("JOIN ROOM")
        if len(players_list) < 2:
            role = random.choice(['X', 'O'])
            for player in players_list:
                if player['role'] == role:
                    role = 'O' if role == 'X' else 'X'
                    break
            players_list.append({
                'user_id': data['user_id'],
                'username': data['username'],
                'role': role
            })

            if len(players_list) == 2:
                game.started = True

            game.players = json.dumps(players_list)
            db.session.commit()

            # Emit aktualizaci do místnosti KDE již hráč je
            emit('game_update', {
                'players': players_list,
                'started': game.started,
                'board': game.board,
                'role': role
            }, room=data['game_uuid'])

            if game.started:
                emit('game_status', {
                    'message': 'Game has started!',
                    'players': players_list
                }, room=data['game_uuid'])

        else:
            players_list.append({
                'user_id': data['user_id'],
                'username': data['username'],
                'role': 'viewer'
            })
            game.players = json.dumps(players_list)
            db.session.commit()

            emit('game_update', {
                'players': players_list,
                'started': game.started,
                'board': game.board,
                'role': 'viewer'
            }, room=data['game_uuid'])

    except Exception as e:
        db.session.rollback()
        emit('error', {'message': f"Error joining game: {str(e)}"}, room=request.sid)

from flask import current_app  # Přidáme import
from extensions import socketio

def handle_make_move(data):
    game = Game.query.filter_by(uuid=data['game_uuid']).first()
    if not game:
        emit('error', {'message': 'Game not found.'}, room=request.sid)
        return
    board = game.board if isinstance(game.board, list) else [[""]*15 for _ in range(15)]
    players_list = json.loads(game.players) if game.players else []
    player = next((p for p in players_list if p['user_id'] == data['player_id']), None)
    if not player or player['role'] == 'viewer':
        emit('error', {'message': 'Invalid move.'}, room=request.sid)
        return
    row, col = data['move']
    if board[row][col] == "":
        board[row][col] = player['role']
        response = call_update_game_api(game.uuid, board, game.name, game.difficulty, data['domain'])
        if response.status_code != 200:
            emit('error', {'message': 'Failed to save game state.'}, room=request.sid)
            return
        game.board = board
        if check_winner(board, player['role']):
            print("HRA VYHRÁNA!!!!!!!!!!")
            game.game_state = 'endgame'
            game.winnerId = player['user_id']
            db.session.commit()
            lossesPlayer = None
            for p in players_list:
                if p['role'] != 'viewer':
                    if p['user_id'] != player['user_id']:
                        lossesPlayer = p['user_id']
                if p['role'] != 'viewer':
                    save_game(game, p["user_id"])
            print("ZAPSAT")
            if game.isRanked:
                update_rating(player['user_id'], lossesPlayer, "wins")
                update_rating(lossesPlayer, player['user_id'], "losses")
        else:
            game.game_state = determine_game_state(board)
            db.session.commit()
        turn = 'X' if player['role'] == 'O' else 'O'
        game.current_turn = turn
        db.session.commit()
        if not game.winnerId:
            if game.uuid in turn_timers:
                turn_timers[game.uuid].cancel()
                del turn_timers[game.uuid]
            app = current_app._get_current_object()  # Get the app instance
            timer = threading.Timer(60.0, handle_turn_timeout, args=[app, socketio, game.uuid, turn])
            turn_timers[game.uuid] = timer
            timer.start()
        emit('game_update', {
            'board': board,
            'players': players_list,
            'started': game.started,
            'turn': turn,
            'game_status': game.game_state,
            "winner": game.winnerId
        }, room=data['game_uuid'])
    else:
        emit('error', {'message': 'Spot taken.'}, room=request.sid)


def handle_turn_timeout(app, socketio_instance, game_uuid, expected_turn):
    with app.app_context():  # Create an application context
        game = Game.query.get(game_uuid)
        if not game or game.winnerId or game.current_turn != expected_turn:
            return
        players = json.loads(game.players)
        winner = next((p['user_id'] for p in players if p['role'] != expected_turn and p['role'] in ['X', 'O']), None)
        if winner:
            game.winnerId = winner
            game.game_state = 'endgame'
            db.session.commit()
            # Use socketio_instance.emit instead of emit
            socketio_instance.emit('game_update', {
                'board': game.board,
                'players': players,
                'started': game.started,
                'turn': game.current_turn,
                'game_status': game.game_state,
                'winner': game.winnerId
            }, room=game_uuid, namespace='/')
            for p in players:
                if p['role'] != 'viewer':
                    save_game(game, p["user_id"])
            if game.uuid in turn_timers:
                del turn_timers[game.uuid]

def handle_player_disconnect(data):
    print("DISCONNECT")
    game = Game.query.filter_by(uuid=data['game_uuid']).first()
    if not game:
        return
    
    players_list = json.loads(game.players) if game.players else []
    if len(players_list) <= 1:
        call_delete_game_api(data['game_uuid'], data['domain'])
        return
    
    if game.uuid in turn_timers:
        timer = turn_timers.pop(game.uuid)
        timer.cancel()

    is_player = False
    winner = ""
    for player in players_list:
        if player['user_id'] == data['user_id'] and player['role'] != 'viewer':
            is_player = True
            winner = next((p['user_id'] for p in players_list if p['role'] != player['role'] and p['role'] != 'viewer'), "")
            break

    if winner != "" and game.winnerId is None and game.isRanked:
        update_rating(winner, data['user_id'], "wins")
        update_rating(data['user_id'], winner, "losses")

    if is_player:
        emit('game_update', {
            'board': data['board1'],
            'players': players_list,
            'started': game.started,
            'turn': 'O' if player['role'] == 'X' else 'X',
            'winner': winner
        }, room=data['game_uuid'])

def register_socket_handlers(socketio):
    socketio.on_event('join_game', handle_join_game)
    socketio.on_event('make_move', handle_make_move)
    socketio.on_event('player_has_disconnected', handle_player_disconnect)