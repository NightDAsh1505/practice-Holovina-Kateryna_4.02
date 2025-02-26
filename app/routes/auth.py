# app/routes/auth.py
from flask import render_template, request, flash, session, redirect, url_for
from . import auth_bp
from ..db import execute_query
from ..helpers import get_role

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = execute_query("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        if user:
            session['user_id'] = user[0]['id']
            session['role'] = get_role(user[0]['id'])
            return redirect(url_for('main_bp.home'))
        else:
            flash("Неправильний логін або пароль!")
    return render_template('login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth_bp.login'))
