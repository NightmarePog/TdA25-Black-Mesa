from flask import Flask, request, jsonify, abort, render_template
from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from datetime import datetime
import hashlib

app = Flask(__name__, template_folder="frontend")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

#-------------------MODELS-------------------
class Game(db.Model):
    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    name = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    game_state = db.Column(db.String(20), nullable=False, default='unknown')
    board = db.Column(db.JSON, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # ID jako auto-increment
    login_by = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=True)  # Heslo může být prázdné pro jiný typ přihlášení

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        """Set SHA-256 hashed password."""
        self.password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        """Check if the provided password matches the stored SHA-256 hash."""
        return self.password_hash == hashlib.sha256(password.encode('utf-8')).hexdigest()
    



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
            
            if User.query.filter_by(username=data['username']).first():
                abort(400, description="Username already exists")

                # Vytvoření nového hráče
            player = User(
                username=data['username'],
                login_by=data['loginBy'],
                email="guest",
                password_hash="guest"
            )

            db.session.add(player)
            db.session.commit()
            return jsonify({"message": "User registered successfully", "id": player.id}), 201
        else:
            # Validace vstupních dat
            if not data.get('username') or not data.get('email'):
                abort(400, description="Username and email are required")
            
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
            return jsonify({"message": "User registered successfully", "id": player.id}), 201
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
        elif player.email == "guest":
            return jsonify({"message": "Cannot log in as a guest", "id": None}), 400
        
        # Pokud se přihlašujeme prostřednictvím vlastní metody (email + heslo)
        if player.login_by == "1" and not player.check_password(data['password']):
            abort(400, description="Invalid credentials")

        # Představme si, že úspěšné přihlášení znamená vrácení ID a nějakého tokenu (v reálném světě by to bylo JWT nebo podobně)
        return jsonify({"message": "Login successful", "id": player.id}), 200

    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))

# Endpoint pro smazání účtu uživatele
@app.route('/api/v1/users/delete', methods=['DELETE'])
def delete_user():
    data = request.get_json()
    try:
        # Ověření, že je poskytnuto ID uživatele
        if not data.get('id'):
            abort(400, description="User ID is required")

        # Vyhledání hráče podle ID
        player = User.query.get(data['id'])
        if not player:
            abort(404, description="User not found")
        
        # Smazání uživatele
        db.session.delete(player)
        db.session.commit()
        
        return jsonify({"message": "User deleted successfully"}), 200

    except KeyError as e:
        abort(400, description=f"Missing field: {str(e)}")
    except Exception as e:
        abort(422, description=str(e))


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
        return False

    # Check for a pattern like "XX XX" or similar
    values = [board[r][c] for r, c in positions]
    empty_count = sum(1 for value in values if value == "")
    player_count = sum(1 for value in values if value == player)

    if empty_count == 1 and player_count == 4:
        return True

    return False

def check_for_five_and_oblique(board):
    """Check if there is a chance to win with 5 in a row or a valid oblique 4-in-a-row."""
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]  # All directions
    for r in range(len(board)):
        for c in range(len(board[0])):
            if board[r][c] != "":
                for direction in directions:
                    if not is_blocked_or_oblique_four(board, r, c, direction):
                        return True
                    if can_win_with_one_move(board, r, c, direction):
                        return True
    return False

def determine_game_state(board):
    # Check if player has the chance to win with 5 in a row or valid oblique 4-in-a-row
    if check_for_five_and_oblique(board):
        return "Koncovka"

    # Placeholder logic for other game states
    x_count = sum(cell == "X" for row in board for cell in row)
    o_count = sum(cell == "O" for row in board for cell in row)
    if x_count + o_count <= 5:
        return "Zahájení"

    return "Middle game"

# Routes for API
@app.route('/api/v1/games', methods=['POST'])
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
            game_state=game_state
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
        game.game_state = determine_game_state(data['board'])
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
        "board": game.board
    }


#-------------------FRONTEND ROUTES-------------------
@app.route('/game', methods=['GET'])
def main_page():
    return render_template('main.html')

@app.route('/game/<uuid>', methods=['GET'])
def game_page(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    return render_template('game.html', game=game_to_dict(game))

# Database Initialization
with app.app_context():
    db.create_all()
    print("Database initialized.")

if __name__ == '__main__':
    app.run(debug=True)
