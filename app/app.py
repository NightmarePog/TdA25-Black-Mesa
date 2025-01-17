from flask import Flask, request, jsonify, abort, render_template, redirect, session, request, json, url_for
from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from datetime import datetime
from flask_socketio import SocketIO, join_room, emit
import hashlib
import json
import requests

app = Flask(__name__, template_folder="frontend")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)

#-------------------MODELS-------------------
class Game(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    name = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    game_state = db.Column(db.String(20), nullable=False, default='unknown')
    board = db.Column(db.JSON, nullable=False)
    players = db.Column(db.JSON, default=[])  # List of players (ID, username, role)
    started = db.Column(db.Boolean, default=False)
    winnerId = db.Column(db.Integer, nullable=True)
    code = db.Column(db.String(6), nullable=True, unique=True)  # 6-character code for game

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Generate a unique 6-character code when creating the game
        self.code = self.generate_unique_code()

    def generate_unique_code(self):
        """Generate a unique 6-character alphanumeric code."""
        while True:
            code = str(uuid4().hex)[:6].lower()
            # Ensure the code is unique
            existing_game = Game.query.filter_by(code=code).first()
            if not existing_game:
                return code

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # ID jako auto-increment
    login_by = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=True)  # Heslo může být prázdné pro jiný typ přihlášení
    saved_games = db.Column(db.JSON, default={})  # Seznam uložených her

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        """Set SHA-256 hashed password."""
        self.password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        """Check if the provided password matches the stored SHA-256 hash."""
        return self.password_hash == hashlib.sha256(password.encode('utf-8')).hexdigest()

@socketio.on('player_has_disconnected')
def player_has_disconnected(data):
    print("Player has disconnected event received")
    print(f"Data received: {data}")  # Debugging: Show received data
    
    game_uuid = data['game_uuid']
    user_id = data['user_id']
    board = data['board1']
    domain = data['domain']
    turn = "X"
    winner = ""
    isPlayer = False
    print("JSEM TASDDDDDDDDDDDDDDDDDDDDD")

    # Získání hry z databáze
    game = Game.query.filter_by(uuid=game_uuid).first()
    if not game:
        emit('error', {'message': 'Game not found.'})
        return
    players_list = json.loads(game.players) if game.players else []

    if len(players_list) <= 1:
        call_delete_game_api(game_uuid, domain)
        print("MAŽU MAPU")
        return

    for player in players_list:
        if player['user_id'] == user_id and player['role'] != 'viewer':
            isPlayer = True
            if player['role'] == 'X':
                turn = 'O'
            for p in players_list:
                if p['role'] != player['role'] and p['role'] != 'viewer':
                    winner = p['user_id']
            break

    if isPlayer:
        emit('game_update', {'board': board, 'players': players_list, 'started': game.started, "turn": turn, "winner": winner}, room=game_uuid)



@socketio.on('join_game')
def handle_join_game(data):
    game_uuid = data['game_uuid']
    user_id = data['user_id']
    username = data['username']
    print(f"User {username} ({user_id}) is trying to join game {game_uuid}")

    # Získání hry z databáze
    game = Game.query.filter_by(uuid=game_uuid).first()
    if not game:
        emit('error', {'message': 'Game not found.'})
        return

    # Convert the players JSON string back to a list
    players_list = json.loads(game.players) if game.players else []

    try:
        # Připojení hráče k hře
        if len(players_list) < 2:
            print(f"User {username} ({user_id}) has joined the game {game_uuid}")
            role = 'X' if len(players_list) == 0 else 'O'
            players_list.append({'user_id': user_id, 'username': username, 'role': role})

            if len(players_list) == 2:
                game.started = True

            # Aktualizace hráčů a uložení změn
            game.players = json.dumps(players_list)
            db.session.commit()

            # Vyslat aktualizaci všem hráčům
            emit('game_update', {
                'players': players_list,
                'started': game.started,
                'board': game.board,  # Poslat aktuální desku
                'role': role
            }, room=game_uuid)

        else:
            # Připojení jako divák
            players_list.append({'user_id': user_id, 'username': username, 'role': 'viewer'})
            game.players = json.dumps(players_list)
            db.session.commit()

            emit('game_update', {
                'players': players_list,
                'started': game.started,
                'board': game.board,
                'role': 'viewer'
            }, room=game_uuid)

        # Připojení do místnosti
        join_room(game_uuid)

        # Pokud hra začala, poslat status
        if game.started:
            emit('game_status', {'message': 'Game has started!', "players": players_list}, room=game_uuid)

    except Exception as e:
        db.session.rollback()
        emit('error', {'message': f"Error joining game: {str(e)}"})
        print(f"Error joining game: {str(e)}")

def save_game(game, player_id):
    user = db.session.get(User, player_id)
    if not user:
        return

    # Načti existující uložené hry, pokud existují, nebo vytvoř nový prázdný slovník.
    saved_games = user.saved_games

    # Pokud je saved_games řetězec (JSON), převedeme jej na slovník.
    if isinstance(saved_games, str):
        saved_games = json.loads(saved_games)

    # Přidej novou hru do slovníku s UUID jako klíčem.
    saved_games[game.uuid] = game_to_dict(game)

    # Ulož zpět do databáze jako JSON řetězec.
    user.saved_games = json.dumps(saved_games)
    db.session.commit()
    print(user.saved_games)  # Tohle vytiskne aktuální seznam uložených her.

def call_delete_game_api(game_uuid, domain):
    base_url = "https://a9334987.app.deploy.tourde.app/"
    if domain != "https://a9334987.app.deploy.tourde.app/" and domain != "":
        base_url = domain

    url = f'{base_url}api/v1/games/{game_uuid}'
    response = requests.delete(url)
    return response

def call_update_game_api(game_uuid, board, name, difficulty, domain):
    base_url = "https://a9334987.app.deploy.tourde.app/"
    if domain != "https://a9334987.app.deploy.tourde.app/" and domain != "":
        base_url = domain

    url = f'{base_url}api/v1/games/{game_uuid}'
    
    data = {
        'name': name,
        'difficulty': difficulty,
        'board': board
    }
    response = requests.put(url, json=data)
    return response

@socketio.on('make_move')
def handle_make_move(data):
    game_uuid = data['game_uuid']
    player_id = data['player_id']
    move = data['move']

    game = Game.query.filter_by(uuid=game_uuid).first()
    if not game:
        emit('error', {'message': 'Game not found.'})
        return

    # Ensure the board is a list of lists, initializing it if necessary.
    board = game.board if isinstance(game.board, list) else [[""] * 15 for _ in range(15)]
    players_list = json.loads(game.players) if game.players else []

    # Find the player by ID.
    player = next((p for p in players_list if p['user_id'] == player_id), None)
    if not player or player['role'] == 'viewer':
        emit('error', {'message': 'Invalid move.'})
        return

    row, col = move
    if board[row][col] == "":
        # Make the player's move.
        board[row][col] = player['role']
        turn = 'X' if player['role'] == 'O' else 'O'
        print(f"Player {player['username']} ({player_id}) made a move at {row}, {col}")

        # Call the API to update the game state.
        response = call_update_game_api(game_uuid, board, game.name, game.difficulty, data['domain'])
        
        if response.status_code != 200:
            print(response.json())
            emit('error', {'message': 'Failed to save the game state via API.'})
            return

        print(f"Board updated successfully for game {game_uuid} via API.")

        # Check if there's a winner
        if check_winner(board, player['role']):
            print(f"Player {player['username']} ({player_id}) wins!")
            # Set the game state to 'finished' when a player wins
            game.game_state = 'endgame'
            db.session.commit()
            # Inform players that the game is over
            #emit('game_over', {'winner': player['username'], 'game_state': game.game_state}, room=game_uuid)
            for p in players_list:
                if p['role'] != 'viewer':
                    save_game(game, p["user_id"])

            emit('game_update', {'board': board, 'players': players_list, 'started': game.started, "turn": turn, "winner": player_id, "game_status": response.json().get('gameState', None)}, room=game_uuid)

        # Inform players about the game update
        emit('game_update', {'board': board, 'players': players_list, 'started': game.started, "turn": turn, "game_status": response.json().get('gameState', None)}, room=game_uuid)
    else:
        emit('error', {'message': 'This spot is already taken.'})






# Funkce pro kontrolu vítěze (5 v řadě)
def check_winner(board, role):
    # Pro zjednodušení se bude kontrolovat pouze horizontálně, vertikálně a diagonálně
    for row in range(15):
        for col in range(15):
            if board[row][col] == role:
                if check_direction(board, row, col, 1, 0, role) or \
                   check_direction(board, row, col, 0, 1, role) or \
                   check_direction(board, row, col, 1, 1, role) or \
                   check_direction(board, row, col, 1, -1, role):
                    return True
    return False

def check_direction(board, row, col, delta_row, delta_col, role):
    count = 0
    for i in range(5):
        r, c = row + i * delta_row, col + i * delta_col
        if 0 <= r < 15 and 0 <= c < 15 and board[r][c] == role:
            count += 1
        else:
            break
    return count == 5





#-------------------ERRORS-------------------
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




#-------------------USER ROUTES-------------------
# Endpoint pro registraci uživatele
@app.route('/api/v1/users/register', methods=['POST'])
def register_user():
    data = request.get_json()
    try:
        #Registrace jako guest
        if data.get('loginBy') == "0" or data.get('loginBy') == 0:
            if not data.get('username'):
                abort(400, description="Username is required")

            # Přidání aktuálního času v sekundách k uživatelskému jménu
            timestamp = int(datetime.now().timestamp())
            data['username'] = f"{data['username']}_{timestamp}"

            if User.query.filter_by(username=data['username']).first():
                abort(400, description="Username already exists")

            # Vytvoření nového hráče
            player = User(
                username=data['username'],
                login_by=data['loginBy'],
                email=str(uuid4()),
                password_hash="guest"
            )

            db.session.add(player)
            db.session.commit()

            return jsonify({
                "message": "User registered successfully",
                "id": player.id,
                "username": player.username
            }), 201
        else:
            # Validace vstupních dat
            if not data.get('username') or not data.get('email'):
                abort(400, description="Username and email are required")
                
            if not data.get('password') and data['loginBy'] == "1":
                abort(400, description="Password is required")
            
            # Kontrola, zda už uživatel existuje
            if User.query.filter_by(username=data['username']).first() or User.query.filter_by(email=data['email']).first():
                abort(400, description="Username or email already exists")

            # Vytvoření nového hráče
            player = User(
                username=data['username'],
                email=data['email'],
                login_by=data['loginBy']
            )
            
            # Pokud je pro přihlášení zvoleno vlastní přihlášení, nastavíme heslo
            if data.get('password'):
                player.set_password(data['password'])

            db.session.add(player)
            db.session.commit()
            return jsonify({"message": "User registered successfully", "id": player.id, "username": player.username}), 201
    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

# Endpoint pro přihlášení uživatele
@app.route('/api/v1/users/login', methods=['POST'])
def login_user():
    data = request.get_json()
    try:
        if data['loginBy'] == "0" or data['loginBy'] == 0:
            return jsonify({"message": "Cannot log in as a guest", "id": None}), 400
        
        # Vyhledání hráče podle emailu
        player = User.query.filter_by(email=data['email']).first()
        if not player:
            abort(404, description="User not found")
        elif player.password_hash == "guest":
            return jsonify({"message": "Cannot log in as a guest", "id": None}), 400
        
        # Pokud se přihlašujeme prostřednictvím vlastní metody (email + heslo)
        if player.login_by == "1" and not player.check_password(data['password']):
            abort(400, description="Invalid credentials")

        # Představme si, že úspěšné přihlášení znamená vrácení ID a nějakého tokenu (v reálném světě by to bylo JWT nebo podobně)
        return jsonify({"message": "Login successful", "id": player.id, "username": player.username}), 200

    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

# Endpoint pro smazání účtu uživatele
@app.route('/api/v1/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 200



# Endpoint pro získání detailu hráče
@app.route('/api/v1/users/<id>', methods=['GET'])
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

@app.route('/api/v1/saved_games/<int:user_id>', methods=['GET'])
def get_saved_games(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

        # Načti existující uložené hry, pokud existují, nebo vytvoř nový prázdný slovník.
    saved_games = user.saved_games

    # Pokud je saved_games řetězec (JSON), převedeme jej na slovník.
    if isinstance(saved_games, str):
        saved_games = json.loads(saved_games)
    games_list = []

    for game_uuid, game_data in saved_games.items():
        game_data["uuid"] = game_uuid  # Přidání UUID do dat pro snadnou identifikaci
        games_list.append(game_data)

    print("************---------------------------")
    print(games_list)
    return jsonify(games_list)

@app.route('/api/v1/saved_games/<int:user_id>/<game_uuid>', methods=['DELETE'])
def delete_saved_game(user_id, game_uuid):
    user = db.session.get(User, user_id)
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
    

@app.route('/api/v1/saved_games/<int:user_id>/<game_uuid>', methods=['GET'])
def get_saved_game(user_id, game_uuid):
    print("GET SAVED GAME")
    user = db.session.get(User, user_id)
    print(user)
    if not user:
        return jsonify({"error": "User not found"}), 404

    saved_games = json.loads(user.saved_games)
    print(game_uuid)
    return jsonify(saved_games[game_uuid])



# Database Initialization
with app.app_context():
    db.create_all()
    print("Player database initialized.")







#-------------------GAME ROUTES-------------------
# Utility Functions
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

def is_blocked_or_oblique_four(board, row, col, direction):
    """Check if a 4-in-a-row is blocked or a valid oblique pattern."""
    dr, dc = direction
    player = board[row][col]
    length = len(board)

    # Check for 5-in-a-row in the given direction
    count = 0
    for i in range(5):
        nr, nc = row + dr * i, col + dc * i
        if 0 <= nr < length and 0 <= nc < length and board[nr][nc] == player:
            count += 1
        else:
            break

    if count == 5:
        return False  # Not blocked, a valid 5-in-a-row

    # Check for 4-in-a-row and if it is blocked
    if count == 4:
        before_row, before_col = row - dr, col - dc
        after_row, after_col = row + dr * 4, col + dc * 4

        before_empty = (0 <= before_row < length and 0 <= before_col < length and board[before_row][before_col] == "")
        after_empty = (0 <= after_row < length and 0 <= after_col < length and board[after_row][after_col] == "")

        if before_empty or after_empty:
            return False  # Not blocked, valid 4-in-a-row with an open end

    # Check for oblique patterns
    if dr in [-1, 1] and dc in [-1, 1]:  # Diagonal direction
        if count == 4:
            if before_empty or after_empty:
                return False  # Oblique pattern valid

    return True  # Blocked

def can_win_with_one_move(board, row, col, direction):
    """Check if adding one move can create a 5-in-a-row."""
    dr, dc = direction
    player = board[row][col]
    length = len(board)

    positions = []
    for i in range(5):
        nr, nc = row + dr * i, col + dc * i
        if 0 <= nr < length and 0 <= nc < length:
            positions.append((nr, nc))

    if len(positions) < 5:
        return [False, None]

    # Check for a pattern like "XX XX" or similar
    values = [board[r][c] for r, c in positions]
    empty_count = sum(1 for value in values if value == "")
    player_count = sum(1 for value in values if value == player)
    
    if empty_count == 1 and player_count == 4:
        for i in values:
            if i != "":
                return [True, i]  # Return player

    return [False, None]

def check_for_five_and_oblique(board):
    """Check if there is a chance to win with 5 in a row or a valid oblique 4-in-a-row."""
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]  # All directions
    for r in range(len(board)):
        for c in range(len(board[0])):
            if board[r][c] != "":
                for direction in directions:
                    #if not is_blocked_or_oblique_four(board, r, c, direction):
                    #    return [True, "None"]  # Immediate win chance
                    func = can_win_with_one_move(board, r, c, direction)
                    print(func)
                    if func[0] == True:  # Check the first element of the returned list
                        return func
    return [False, None]  # Ensure consistent return type

def determine_game_state(board):
    # Placeholder logic for other game states
    x_count = sum(cell == "X" for row in board for cell in row)
    o_count = sum(cell == "O" for row in board for cell in row)

    # Check if player has the chance to win with 5 in a row or valid oblique 4-in-a-row
    if check_winner(board, "X"):
        return "endgame"
    if check_winner(board, "O"):
        return "endgame"
    
    result = check_for_five_and_oblique(board)
    print(result)
    if result and result[0]:  # Make sure the result is not None and check the first element
        print(x_count, o_count)
        if x_count == o_count and result[1] == "O":
            print("11111111")
            return "midgame"
        elif x_count == o_count + 1 and result[1] == "X":
            print("HRÁČ 2 TO MŮŽE ZASTAVIT")
            return "midgame"
            
        print("VRACÍM ENDGAME")
        return "endgame"

    if x_count + o_count <= 5:
        return "opening"

    return "midgame"



# Routes for API
@app.route('/api/v1/games', methods=['POST'])
def create_game():
    data = request.get_json()
    try:
        print(data)
        is_valid, error = validate_game(data['board'])
        if not is_valid:
            abort(400, description=error)
        game_state = determine_game_state(data['board'])
        game = Game(
            name=data['name'],
            difficulty=data['difficulty'],
            board=data['board'],
            game_state=game_state,
            players=data.get('players')
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

@app.route('/api/v1/get_game_data_by_code/<code>', methods=['GET'])
def get_game_data_by_code(code):
    game = Game.query.filter_by(code=code).first()
    if not game:
        abort(404)
    return jsonify(game_to_dict(game)), 200

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
        is_valid, error = validate_game(data['board'])
        if not is_valid:
            abort(400, description=error)
        game.name = data['name']
        game.difficulty = data['difficulty']
        game.board = data['board']
        players = game.players
        if isinstance(players, str):
            players = json.loads(game.players)

        if check_winner(data['board'], "X"):
            game.game_state = 'endgame'

            for value in players:
                if value['role'] == "X":
                    game.winnerId = value['user_id']

        elif check_winner(data['board'], "O"):
            game.game_state = 'endgame'
            
            for value in players:
                print(value)
                if value['role'] == "O":
                    game.winnerId = value['user_id']
        else:
            game.game_state = determine_game_state(data['board'])

        if data.get("save_game_to_user"):
            for value in players:
                if value["role"] == "X" or value["role"] == "O":
                    save_game(game, data.get("save_game_to_user"))

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
        "board": game.board,
        "code": game.code,
        "winnerId": game.winnerId,
        "players": game.players
    }


#-------------------FRONTEND ROUTES-------------------
@app.route('/game/<uuid>', methods=['GET'])
def saved_game_page(uuid):
    return render_template('saved_game.html', uuid=uuid)

@app.route('/menu', methods=['GET'])
def menu_page():
    return render_template('menu.html')

@app.route('/game', methods=['GET'])
def main_page():
    return render_template('game.html')

@app.route('/', methods=['GET'])
def start_page():
    return redirect("/login")

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/multiplayer-game/<uuid>', methods=['GET'])
def game_page(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    return render_template('multiplayer_game.html', game=game_to_dict(game))

# Database Initialization
with app.app_context():
    db.create_all()
    print("Database initialized.")

if __name__ == '__main__':
    app.run(debug=True)
