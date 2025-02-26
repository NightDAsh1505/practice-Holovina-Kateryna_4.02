# app/config.py
import os

class Config:
    """Базова конфігурація для Flask додатку."""
    # Можна зберігати ключ у змінній середовища або прописати тут "заглушку".
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_default_secret_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Якщо ви використовуєте SQLAlchemy, тут може бути URI:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:your_password@localhost:5432/scanlation_project_management'

    # Де зберігати файли (відносно кореня проекту)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf', 'jpg', 'jpeg', 'png', 'txt'}

    # Можна додати обмеження в 16MB
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024