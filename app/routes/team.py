# app/routes/team.py
from flask import render_template, redirect, url_for, request, flash, session
from . import team_bp
from ..db import execute_query, execute_non_select
from ..helpers import get_role, is_admin

@team_bp.route('/team')
def team():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))

    users = execute_query("SELECT * FROM users")
    for u in users:
        u['role'] = get_role(u['id'])
    return render_template('team.html', users=users)

@team_bp.route('/team/create_user', methods=['GET', 'POST'])
def create_user():
    if not is_admin():
        flash("У вас немає прав для створення користувачів.")
        return redirect(url_for('team_bp.team'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_id = request.form.get('role_id')

        execute_non_select("INSERT INTO users (username, email, password, role_id) VALUES (%s, %s, %s, %s)",
                           (username, email, password, role_id))
        flash("Новий користувач створений.")
        return redirect(url_for('team_bp.team'))

    roles = execute_query("SELECT id, name FROM roles")
    return render_template('create_user.html', roles=roles)

@team_bp.route('/user/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if not is_admin():
        flash("У вас немає прав для видалення користувачів.")
        return redirect(url_for('team_bp.team'))

    execute_non_select("DELETE FROM users WHERE id=%s", (user_id,))
    flash("Користувача видалено.")
    return redirect(url_for('team_bp.team'))

################################################################################
# РЕДАГУВАННЯ КОРИСТУВАЧА
################################################################################
@team_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    """
    Редагування (username, email, password, role) - лише Адміністратор.
    """
    if not is_admin():
        flash("У вас немає прав для редагування користувачів.")
        return redirect(url_for('team_bp.team'))

    # 1) Знайти користувача
    row = execute_query("SELECT * FROM users WHERE id=%s", (user_id,))
    if not row:
        flash("Користувача не знайдено.")
        return redirect(url_for('team_bp.team'))
    user = row[0]

    if request.method == 'POST':
        # Отримати нові дані з форми
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_password = request.form.get('password')
        new_role_id = request.form.get('role_id')

        # Оновити
        upd_query = """
            UPDATE users
            SET username=%s,
                email=%s,
                password=%s,
                role_id=%s
            WHERE id=%s
        """
        execute_non_select(upd_query, (new_username, new_email, new_password, new_role_id, user_id))
        flash("Дані користувача оновлено.")
        return redirect(url_for('team_bp.team'))

    # Якщо GET — показати форму
    roles = execute_query("SELECT id, name FROM roles")
    return render_template('edit_user.html', user=user, roles=roles)
