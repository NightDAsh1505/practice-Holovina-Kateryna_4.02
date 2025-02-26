# app/routes/comments.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db import execute_query, execute_non_select
from ..helpers import get_role, user_is_coordinator_of, is_admin
from ..helpers import get_subtask_full, user_can_view_subtask, user_can_comment, user_can_edit_comment
from datetime import datetime
from . import comments_bp


@comments_bp.route('/comment/subtask/<int:subtask_id>/create', methods=['POST'])
def create_comment(subtask_id):
    if 'user_id' not in session:
        flash("Авторизуйтесь.")
        return redirect(url_for('auth_bp.login'))

    subtask = get_subtask_full(subtask_id)
    if not subtask:
        flash("Підзавдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    # Перевірити, чи користувач може коментувати
    if not user_can_comment(subtask):
        flash("У вас немає прав, щоб лишати коментар.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))

    content = request.form.get('content', '').strip()
    if not content:
        flash("Неможливо створити порожній коментар.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))

    user_id = session['user_id']
    ins_q = """
      INSERT INTO comments (subtask_id, user_id, content)
      VALUES (%s, %s, %s)
    """
    execute_non_select(ins_q, (subtask_id, user_id, content))
    flash("Коментар додано.")
    return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))


@comments_bp.route('/comment/<int:comment_id>/edit', methods=['GET','POST'])
def edit_comment(comment_id):
    if 'user_id' not in session:
        flash("Авторизуйтесь.")
        return redirect(url_for('auth_bp.login'))

    # Знайти коментар
    row = execute_query("SELECT * FROM comments WHERE id=%s", (comment_id,))
    if not row:
        flash("Коментар не знайдено.")
        return redirect(url_for('projects_bp.projects'))
    comment_row = row[0]

    # Знайти subtask
    subtask = get_subtask_full(comment_row['subtask_id'])
    if not subtask:
        flash("Підзавдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    # Якщо коментар is_deleted => не дозволяємо редагувати
    if comment_row['is_deleted']:
        flash("Цей коментар видалено, його не можна редагувати.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask['id']))

    # Перевірити права
    if not user_can_edit_comment(comment_row, subtask):
        flash("У вас немає прав редагувати цей коментар.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask['id']))

    if request.method == 'POST':
        new_content = request.form.get('content', '').strip()
        if not new_content:
            flash("Порожній коментар.")
            return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask['id']))

        upd_q = """
          UPDATE comments
          SET content=%s, updated_at=NOW()
          WHERE id=%s
        """
        execute_non_select(upd_q, (new_content, comment_id))
        flash("Коментар змінено.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask['id']))

    return render_template('edit_comment.html', comment_row=comment_row, subtask=subtask)


@comments_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        flash("Авторизуйтесь.")
        return redirect(url_for('auth_bp.login'))

    row = execute_query("SELECT * FROM comments WHERE id=%s", (comment_id,))
    if not row:
        flash("Коментар не знайдено.")
        return redirect(url_for('projects_bp.projects'))
    comment_row = row[0]

    subtask = get_subtask_full(comment_row['subtask_id'])
    if not subtask:
        flash("Підзавдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    if not user_can_edit_comment(comment_row, subtask):
        flash("У вас немає прав видалити цей коментар.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask['id']))

    del_q = """
      UPDATE comments
      SET is_deleted=TRUE, content='', updated_at=NOW()
      WHERE id=%s
    """
    execute_non_select(del_q, (comment_id,))
    flash("Коментар видалено.")
    return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask['id']))
