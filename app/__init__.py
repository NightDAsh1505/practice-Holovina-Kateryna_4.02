# app/__init__.py
from flask import Flask
from .config import Config
from .routes import init_routes
import os
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)


    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    # Реєструємо всі наші Blueprint-и
    init_routes(app)

    @app.template_filter('strftime')
    def strftime_filter(value, format="%d/%m/%Y %H:%M"):
        if not value:
            return ""
        return value.strftime(format)

    return app
