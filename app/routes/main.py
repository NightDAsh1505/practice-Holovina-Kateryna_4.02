# app/routes/main.py
from flask import render_template, session, redirect, url_for
from . import main_bp

@main_bp.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))
    return render_template('home.html')
