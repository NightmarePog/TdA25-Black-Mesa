from flask import Blueprint, render_template, redirect, url_for, abort
from models import Game
from models import User
from utils import game_to_dict

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/game/<uuid>')
def saved_game_page(uuid):
    return render_template('saved_game.html', uuid=uuid)

@frontend_bp.route('/menu')
def menu_page():
    return render_template('menu.html')

@frontend_bp.route('/game')
def main_page():
    return render_template('game.html')

@frontend_bp.route('/')
def start_page():
    return redirect("/login")

@frontend_bp.route('/login')
def login_page():
    return render_template('login.html')

@frontend_bp.route('/register')
def register_page():
    return render_template('register.html')

@frontend_bp.route('/list')
def users_list():
    return render_template('users_list.html')

@frontend_bp.route('/multiplayer-game/<uuid>')
def game_page(uuid):
    game = Game.query.get(uuid)
    if not game:
        abort(404)
    return render_template('multiplayer_game.html', game=game_to_dict(game))

@frontend_bp.route('/user/<uuid>')
def user_page(uuid):
    user_info = User.query.get(uuid)
    if not user_info:
        abort(404)
    return render_template('user_page.html', user_info=user_info)

@frontend_bp.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html')