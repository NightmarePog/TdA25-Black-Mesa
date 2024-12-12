import os

from flask import Flask
from . import db
#TEMP VARIABLE
gameid = "1"
app = Flask(__name__)

app.config.from_mapping(
    DATABASE=os.path.join(app.instance_path, 'tourdeflask.sqlite'),
)

# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

db.init_app(app)

def error_handler(errorCode):
    pass

@app.route('/')
def root_page():
    return "Hello TdA"

@app.route('/games', methods=['GET'])
def create_game():
    # TODO creates new game
    return None

@app.route('/games', methods=['POST'])
def get_games():
    # TODO creates new game
    return None

@app.route('/games/'+gameid, methods=['GET'])
def get_game():
    return "I work!"

@app.route('/games/'+gameid, methods=['PUT'])
def set_game():
    return None

@app.route('/games/'+gameid, methods=['DELETE'])
def delete_game():
    return None

if __name__ == '__main__':
    app.run()
