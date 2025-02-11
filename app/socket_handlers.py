from extensions import db, socketio
from flask import request
from models import Game, User
import json
from utils import check_winner, game_to_dict, save_game, call_delete_game_api, call_update_game_api, determine_game_state
import requests

def handle_join_game(data):
    game = Game.query.filter_by(uuid=data['game_uuid']).first()
    if not game:
        socketio.emit('error', {'message': 'Game not found.'}, room=request.sid)
        return
    players_list = json.loads(game.players) if game.players else []
    try:
        if len(players_list) < 2:
            role = 'X' if len(players_list) == 0 else 'O'
            players_list.append({'user_id': data['user_id'], 'username': data['username'], 'role': role})
            if len(players_list) == 2:
                game.started = True
            game.players = json.dumps(players_list)
            db.session.commit()
            socketio.emit('game_update', {
                'players': players_list,
                'started': game.started,
                'board': game.board,
                'role': role
            }, room=data['game_uuid'])
        else:
            players_list.append({'user_id': data['user_id'], 'username': data['username'], 'role': 'viewer'})
            game.players = json.dumps(players_list)
            db.session.commit()
            socketio.emit('game_update', {
                'players': players_list,
                'started': game.started,
                'board': game.board,
                'role': 'viewer'
            }, room=data['game_uuid'])
        socketio.join_room(data['game_uuid'])
        if game.started:
            socketio.emit('game_status', {'message': 'Game has started!', "players": players_list}, room=data['game_uuid'])
    except Exception as e:
        db.session.rollback()
        socketio.emit('error', {'message': f"Error joining game: {str(e)}"}, room=request.sid)

def handle_make_move(data):
    print("sdfsdfsdf")
    game = Game.query.filter_by(uuid=data['game_uuid']).first()
    if not game:
        socketio.emit('error', {'message': 'Game not found.'}, room=request.sid)
        return
    board = game.board if isinstance(game.board, list) else [[""]*15 for _ in range(15)]
    players_list = json.loads(game.players) if game.players else []
    player = next((p for p in players_list if p['user_id'] == data['player_id']), None)
    if not player or player['role'] == 'viewer':
        socketio.emit('error', {'message': 'Invalid move.'}, room=request.sid)
        return
    row, col = data['move']
    if board[row][col] == "":
        board[row][col] = player['role']
        response = call_update_game_api(game.uuid, board, game.name, game.difficulty, data['domain'])
        if response.status_code != 200:
            socketio.emit('error', {'message': 'Failed to save game state.'}, room=request.sid)
            return
        game.board = board
        if check_winner(board, player['role']):
            game.game_state = 'endgame'
            game.winnerId = player['user_id']
            db.session.commit()
            for p in players_list:
                if p['role'] != 'viewer':
                    save_game(game, p["user_id"])
        else:
            game.game_state = determine_game_state(board)
            db.session.commit()
        turn = 'X' if player['role'] == 'O' else 'O'
        socketio.emit('game_update', {
            'board': board,
            'players': players_list,
            'started': game.started,
            'turn': turn,
            'game_status': response.json().get('gameState')
        }, room=data['game_uuid'])
    else:
        socketio.emit('error', {'message': 'Spot taken.'}, room=request.sid)

def handle_player_disconnect(data):
    game = Game.query.filter_by(uuid=data['game_uuid']).first()
    if not game:
        return
    players_list = json.loads(game.players) if game.players else []
    if len(players_list) <= 1:
        call_delete_game_api(data['game_uuid'], data['domain'])
        return
    is_player = False
    winner = ""
    for player in players_list:
        if player['user_id'] == data['user_id'] and player['role'] != 'viewer':
            is_player = True
            winner = next((p['user_id'] for p in players_list if p['role'] != player['role'] and p['role'] != 'viewer'), "")
            break
    if is_player:
        socketio.emit('game_update', {
            'board': data['board'],
            'players': players_list,
            'started': game.started,
            'turn': 'O' if player['role'] == 'X' else 'X',
            'winner': winner
        }, room=data['game_uuid'])

def register_socket_handlers(socketio):
    socketio.on_event('join_game', handle_join_game)
    socketio.on_event('make_move', handle_make_move)
    socketio.on_event('player_has_disconnected', handle_player_disconnect)