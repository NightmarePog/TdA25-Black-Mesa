from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, emit

db = SQLAlchemy()
socketio = SocketIO()