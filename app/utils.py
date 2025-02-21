from extensions import db
from models import Game, User
from datetime import datetime
from flask import jsonify, abort, redirect, url_for, request, render_template
import json
import requests

# Error handlers
def handle_errors(app):
    @app.errorhandler(400)
    def bad_request(error):
        return redirect(url_for('error_page', code=400))

    @app.errorhandler(404)
    def not_found(error ):
        redirect(url_for('error_page', code=404))
        return redirect(url_for('error_page', code=404))

    @app.errorhandler(422)
    def unprocessable_entity(error):
        redirect(url_for('error_page', code=422))
        return redirect(url_for('error_page', code=422))
    
    @app.route('/error')
    def error_page():
        error_code = request.args.get('code', default='404')
        return render_template('error.html', error_code=error_code)


def update_rating(user_id, user2_id, type,num=None):
    user = User.query.get(user_id)
    user2 = User.query.get(user2_id)

    if not num:
        num = 1

    if not user:
        return
    if type == "wins":
        user.wins += num
        num = 1

    elif type == "draws":
        user.draws += num
        num = 0.5

    elif type == "losses":
        user.losses += num
        num = 0
    
    e = 1 / (1 + 10 * ((user2.elo - user.elo) / 400))
    newRating = user.elo + 40 * ((num - e) * (1 + 0.5 * (0.5 - ((user.wins + user.draws) / (user.wins + user.draws + user.losses)))))
    user.elo = newRating
    db.session.commit()

# Game validation and logic
def validate_game(board):
    if len(board) != 15 or any(len(row) != 15 for row in board):
        return False, "Invalid board dimensions"
    valid_symbols = {"X", "O", ""}
    for row in board:
        if any(cell not in valid_symbols for cell in row):
            return False, "Invalid symbols on the board"
    x_count = sum(cell == "X" for row in board for cell in row)
    o_count = sum(cell == "O" for row in board for cell in row)
    if not (x_count == o_count or x_count == o_count + 1):
        return False, "Invalid number of moves"
    return True, None

def check_winner(board, symbol):
    for row in range(15):
        for col in range(15):
            if board[row][col] == symbol:
                # Check horizontal
                if col <= 10 and all(board[row][col+i] == symbol for i in range(5)):
                    return True
                # Check vertical
                if row <= 10 and all(board[row+i][col] == symbol for i in range(5)):
                    return True
                # Check diagonal down
                if row <= 10 and col <= 10 and all(board[row+i][col+i] == symbol for i in range(5)):
                    return True
                # Check diagonal up
                if row >= 4 and col <= 10 and all(board[row-i][col+i] == symbol for i in range(5)):
                    return True
    return False

def game_to_dict(game):
    return {
        "uuid": game.uuid,
        "createdAt": game.created_at.isoformat(),
        "updatedAt": game.updated_at.isoformat(),
        "name": game.name,
        "difficulty": game.difficulty,
        "gameState": game.game_state,
        "board": game.board,
        "code": game.code,
        "winnerId": game.winnerId,
        "players": game.players
    }

def user_to_dict(user):
    return {
        "uuid": user.uuid,
        "createdAt": user.created_at.isoformat(),
        "loginBy": user.login_by,
        "username": user.username,
        "email": user.email,
        "wins": user.wins,
        "draws": user.draws,
        "losses": user.losses,
        "elo": user.elo
    }

def save_game(game, player_id):
    user = User.query.get(player_id)
    print(user)
    if not user:
        return
    saved_games = json.loads(user.saved_games) if isinstance(user.saved_games, str) else user.saved_games
    saved_games[game.uuid] = game_to_dict(game)
    user.saved_games = json.dumps(saved_games)
    db.session.commit()

# utils.py

def determine_game_state(board):
    x_count = sum(cell == "X" for row in board for cell in row)
    o_count = sum(cell == "O" for row in board for cell in row)

    # Check if someone has already won
    if check_winner(board, "X") or check_winner(board, "O"):
        return "endgame"
    
    # Check for potential winning patterns
    result = check_for_five_and_oblique(board)
    if result and result[0]:
        if (x_count == o_count and result[1] == "O") or \
           (x_count == o_count + 1 and result[1] == "X"):
            return "midgame"
        return "endgame"

    # Early game detection
    if x_count + o_count <= 5:
        return "opening"

    return "midgame"

def check_for_five_and_oblique(board):
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
    for r in range(len(board)):
        for c in range(len(board[0])):
            if board[r][c] != "":
                for direction in directions:
                    if can_win_with_one_move(board, r, c, direction)[0]:
                        return [True, board[r][c]]
    return [False, None]

def can_win_with_one_move(board, row, col, direction):
    dr, dc = direction
    player = board[row][col]
    positions = []
    for i in range(5):
        nr, nc = row + dr * i, col + dc * i
        if 0 <= nr < 15 and 0 <= nc < 15:
            positions.append((nr, nc))
    
    if len(positions) < 5:
        return [False, None]
    
    values = [board[r][c] for r, c in positions]
    empty_count = sum(1 for value in values if value == "")
    player_count = sum(1 for value in values if value == player)
    
    if empty_count == 1 and player_count == 4:
        return [True, player]
    
    return [False, None]

def call_delete_game_api(game_uuid, domain):
    base_url = "https://a9334987.app.deploy.tourde.app/"
    if domain not in [base_url, ""]:
        base_url = domain
    response = requests.delete(f'{base_url}api/v1/games/{game_uuid}')
    return response

def call_update_game_api(game_uuid, board, name, difficulty, domain):
    base_url = "https://a9334987.app.deploy.tourde.app/"
    if domain not in [base_url, ""]:
        base_url = domain
    response = requests.put(
        f'{base_url}api/v1/games/{game_uuid}',
        json={'name': name, 'difficulty': difficulty, 'board': board}
    )
    return response