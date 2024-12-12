import os

from flask import Flask
from . import db

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


@app.route('/')
def root_page():
    return "Hello TdA"

@app.route('/games', methods=['GET'])
def hello_world():
    # TODO creates new game
    return None


if __name__ == '__main__':
    app.run()
