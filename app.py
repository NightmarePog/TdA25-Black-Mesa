from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# Inicializace Flask aplikace
app = Flask(__name__)

# Konfigurace SQLite databáze
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///games.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Databázový model
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    size = db.Column(
        db.String(10), nullable=False
    )  # Velikost herní desky (např. "6x6")
    occupied = db.Column(
        db.Text, nullable=False
    )  # Statistika obsazených polí (JSON formát)


# Inicializace databáze
with app.app_context():
    db.create_all()


@app.route("/games/<int:id>", methods=["PUT"])
def update_game(id):
    game = Game.query.get_or_404(
        id
    )  # Najde hru podle ID, pokud neexistuje, vrátí chybu 404
    data = request.get_json()  # Získá data z těla požadavku

    # Aktualizuje atributy hry podle nových dat
    game.name = data.get("name", game.name)
    game.difficulty = data.get("difficulty", game.difficulty)
    game.size = data.get("size", game.size)
    game.occupied = data.get("occupied", game.occupied)

    db.session.commit()  # Uloží změny do databáze

    return jsonify({"message": "Game updated!"})


# API endpointy
@app.route("/games", methods=["GET"])
def get_games():
    games = Game.query.all()  # Získá všechny hry z databáze
    return jsonify(
        [
            {
                "id": game.id,
                "name": game.name,
                "difficulty": game.difficulty,
                "size": game.size,
                "occupied": game.occupied,
            }
            for game in games  # Iteruje přes všechny hry a vytváří seznam slovníků
        ]
    )


@app.route("/games", methods=["POST"])
def create_game():
    data = request.get_json()
    new_game = Game(
        name=data["name"],
        difficulty=data["difficulty"],
        size=data["size"],  # Velikost herní desky (např. "6x6")
        occupied=data["occupied"],  # Statistika obsazených polí ve formátu JSON
    )
    db.session.add(new_game)
    db.session.commit()
    return jsonify({"message": "Game created!"}), 201


@app.route("/games/<int:id>", methods=["GET"])
def get_game(id):
    game = Game.query.get_or_404(id)
    return jsonify(
        {
            "id": game.id,
            "name": game.name,
            "difficulty": game.difficulty,
            "size": game.size,
            "occupied": game.occupied,
        }
    )


@app.route("/games/<int:id>", methods=["DELETE"])
def delete_game(id):
    game = Game.query.get_or_404(id)
    db.session.delete(game)
    db.session.commit()
    return jsonify({"message": "Game deleted!"})


if __name__ == "__main__":
    app.run(debug=True)
