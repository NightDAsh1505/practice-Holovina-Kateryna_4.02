# app/routes/__init__.py
from flask import Blueprint

# Створюємо по одному Blueprint на кожен логічний модуль
auth_bp = Blueprint('auth_bp', __name__)
main_bp = Blueprint('main_bp', __name__)
projects_bp = Blueprint('projects_bp', __name__)
subtasks_bp = Blueprint('subtasks_bp', __name__)
team_bp = Blueprint('team_bp', __name__)
comments_bp = Blueprint('comments_bp', __name__)

# Імпортуємо модулі, де оголошені rout-и
from . import auth, main, projects, subtasks, team, comments

def init_routes(app):
    """
    Реєструємо всі Blueprint'и.
    """
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(subtasks_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(comments_bp)
