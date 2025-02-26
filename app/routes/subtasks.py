# app/routes/subtasks.py
import os
from flask import render_template, redirect, url_for, request, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from flask import current_app

from . import subtasks_bp
from ..db import execute_query, execute_non_select
from ..helpers import (
    is_admin,
    user_is_coordinator_of,
    get_role_name,
    get_username,
    get_role_id_by_name,
    get_role,
    allowed_file,
    get_subtask_full,
    user_can_view_subtask,
    user_can_upload_subtask,
    user_can_delete_file,
    user_can_download_file,
    user_can_comment,
    user_can_edit_comment
)

@subtasks_bp.route('/project/<int:project_id>/project_task/<int:ptask_id>')
def project_task_detail(project_id, ptask_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))

    # Витягнемо сам project_task
    ptask = execute_query(
        "SELECT * FROM project_tasks WHERE id=%s AND project_id=%s",
        (ptask_id, project_id)
    )
    if not ptask:
        flash("Верхнє завдання не знайдено.")
        return redirect(url_for('projects_bp.project_detail', project_id=project_id))

    project_task = ptask[0]

    # Витягнемо назву проєкту + координатора
    prow = execute_query(
        "SELECT p.name AS project_name, p.coordinator_id FROM projects p WHERE p.id=%s",
        (project_id,)
    )
    if prow:
        project_name = prow[0]['project_name']
        project_coordinator_id = prow[0]['coordinator_id']
    else:
        project_name = "N/A"
        project_coordinator_id = None

    # Підзавдання
    subtasks = execute_query("SELECT * FROM subtasks WHERE project_task_id=%s", (ptask_id,))
    if subtasks:
        for s in subtasks:
            s['assigned_role_name'] = get_role_name(s['assigned_role'])
            s['assigned_user_name'] = get_username(s['assigned_user'])

    user_id = session.get('user_id')
    can_edit_task = False
    if session.get('role') == 'Адміністратор':
        can_edit_task = True
    else:
        if project_coordinator_id and user_id == project_coordinator_id:
            can_edit_task = True

    return render_template(
        'project_task_detail.html',
        project_id=project_id,
        project_name=project_name,
        project_coordinator_id=project_coordinator_id,
        project_task=project_task,
        subtasks=subtasks,
        can_edit_task=can_edit_task
    )


@subtasks_bp.route('/project/<int:project_id>/project_task/<int:ptask_id>/create_subtask', methods=['GET', 'POST'])
def create_subtask(project_id, ptask_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))

    if not (is_admin() or user_is_coordinator_of(project_id)):
        flash("У вас немає прав для створення підзавдань у цьому проєкті.")
        return redirect(url_for('subtasks_bp.project_task_detail', project_id=project_id, ptask_id=ptask_id))

    ptask = execute_query(
        "SELECT * FROM project_tasks WHERE id=%s AND project_id=%s",
        (ptask_id, project_id)
    )
    if not ptask:
        flash("Верхнє завдання не знайдено.")
        return redirect(url_for('projects_bp.project_detail', project_id=project_id))

    if request.method == 'POST':
        name = request.form.get('name')
        deadline = request.form.get('deadline')
        status = request.form.get('status')
        assigned_role = request.form.get('assigned_role')
        assigned_user = request.form.get('assigned_user')

        ins_query = """
            INSERT INTO subtasks (project_task_id, name, deadline, status, assigned_role, assigned_user)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        row = execute_query(ins_query, (ptask_id, name, deadline, status, assigned_role, assigned_user))
        new_subtask_id = row[0]['id']
        flash("Підзавдання створено!")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=new_subtask_id))

    subtask_statuses = ["В черзі", "В роботі", "Прострочено", "Виконано"]
    translator_role_id = get_role_id_by_name("Перекладач")
    worker_role_id = get_role_id_by_name("Працівник")

    translator_users = execute_query("SELECT id, username FROM users WHERE role_id=%s", (translator_role_id,))
    worker_users = execute_query("SELECT id, username FROM users WHERE role_id=%s", (worker_role_id,))

    return render_template(
        'create_subtask.html',
        project_id=project_id,
        ptask_id=ptask_id,
        subtask_statuses=subtask_statuses,
        translator_role_id=translator_role_id,
        worker_role_id=worker_role_id,
        translator_users=translator_users,
        worker_users=worker_users
    )

@subtasks_bp.route('/subtask/<int:subtask_id>/delete', methods=['POST'])
def delete_subtask(subtask_id):

    if 'user_id' not in session:
        flash("Спочатку авторизуйтесь.")
        return redirect(url_for('auth_bp.login'))

    row = execute_query("SELECT project_task_id FROM subtasks WHERE id=%s", (subtask_id,))
    if not row:
        flash("Підзавдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    parent_task_id = row[0]['project_task_id']
    row2 = execute_query("SELECT project_id FROM project_tasks WHERE id=%s", (parent_task_id,))
    if not row2:
        flash("Верхнє завдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    project_id = row2[0]['project_id']

    if not (is_admin() or user_is_coordinator_of(project_id)):
        flash("У вас немає прав для видалення підзавдання.")
        return redirect(url_for('subtasks_bp.project_task_detail', project_id=project_id, ptask_id=parent_task_id))

    execute_non_select("DELETE FROM subtasks WHERE id=%s", (subtask_id,))
    flash("Підзавдання видалено.")
    return redirect(url_for('subtasks_bp.project_task_detail', project_id=project_id, ptask_id=parent_task_id))

@subtasks_bp.route('/subtask/<int:subtask_id>')
def view_subtask(subtask_id):

    subtask = get_subtask_full(subtask_id)
    if not subtask:
        flash("Підзавдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    if not user_can_view_subtask(subtask):
        flash("У вас немає прав переглядати це підзавдання.")
        return redirect(url_for('projects_bp.projects'))

    comments_query = """
      SELECT c.*, u.username
      FROM comments c
      JOIN users u ON c.user_id = u.id
      WHERE c.subtask_id=%s
      ORDER BY c.created_at ASC
    """
    all_comments = execute_query(comments_query, (subtask_id,))

    for c in all_comments:
        c['can_edit'] = user_can_edit_comment(c, subtask)

    can_add_comment = user_can_comment(subtask)

    attach_query = """
        SELECT a.*, u.username AS uploader_username
        FROM attachments a
        JOIN users u ON a.uploader_id = u.id
        WHERE a.subtask_id=%s
        ORDER BY a.uploaded_at DESC
    """
    attachments = execute_query(attach_query, (subtask_id,))

    row_ptask = execute_query("""
        SELECT pt.name as task_name, pt.project_id, p.name as project_name
        FROM project_tasks pt
        JOIN projects p ON pt.project_id = p.id
        WHERE pt.id=%s
    """, (subtask['project_task_id'],))
    if row_ptask:
        task_name = row_ptask[0]['task_name']
        project_name = row_ptask[0]['project_name']
    else:
        task_name = "N/A"
        project_name = "N/A"

    return render_template(
        'subtask_detail.html',
        subtask=subtask,
        attachments=attachments,
        comments=all_comments,
        can_add_comment=can_add_comment,
        task_name=task_name,
        project_name=project_name,
        can_upload_file=user_can_upload_subtask(subtask),
        user_can_delete_file=user_can_delete_file
    )

@subtasks_bp.route('/subtask/<int:subtask_id>/upload', methods=['POST'])
def upload_attachment(subtask_id):

    subtask = get_subtask_full(subtask_id)
    if not subtask:
        flash("Підзавдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    if not user_can_upload_subtask(subtask):
        flash("У вас немає прав завантажувати файл до цього підзавдання.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))

    if 'file' not in request.files:
        flash("Не вибрано файл.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))

    file_ = request.files['file']
    if file_.filename == '':
        flash("Не вибрано файл.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))

    if file_ and allowed_file(file_.filename):
        filename = secure_filename(file_.filename)

        subfolder = f"subtask_{subtask_id}"
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file_path = os.path.join(upload_folder, filename)
        file_.save(file_path)

        rel_path = f"uploads/{subfolder}/{filename}"

        user_id = session['user_id']
        ins_q = """
            INSERT INTO attachments (subtask_id, uploader_id, file_path, original_name)
            VALUES (%s, %s, %s, %s)
        """
        execute_non_select(ins_q, (subtask_id, user_id, rel_path, file_.filename))
        flash("Файл успішно завантажений.")
    else:
        flash("Недопустимий формат файлу.")

    return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))


@subtasks_bp.route('/attachment/<int:attachment_id>/download')
def download_attachment(attachment_id):

    row = execute_query("SELECT * FROM attachments WHERE id=%s", (attachment_id,))
    if not row:
        flash("Файл не знайдено.")
        return redirect(url_for('projects_bp.projects'))
    attach = row[0]

    subtask = get_subtask_full(attach['subtask_id'])
    if not subtask:
        flash("Підзавдання не знайдено (для файлу).")
        return redirect(url_for('projects_bp.projects'))

    if not user_can_download_file(subtask):
        flash("У вас немає прав скачувати цей файл.")
        return redirect(url_for('projects_bp.projects'))

    full_path = os.path.join(current_app.config['BASE_DIR'], attach['file_path'])
    if not os.path.exists(full_path):
        flash("Файл не знайдено на диску.")
        return redirect(url_for('projects_bp.projects'))

    return send_from_directory(
        directory=os.path.dirname(full_path),
        path=os.path.basename(full_path),
        as_attachment=True,
        download_name=attach['original_name']
    )


@subtasks_bp.route('/attachment/<int:attachment_id>/delete', methods=['POST'])
def delete_attachment(attachment_id):

    row = execute_query("SELECT * FROM attachments WHERE id=%s", (attachment_id,))
    if not row:
        flash("Файл не знайдено.")
        return redirect(url_for('projects_bp.projects'))
    attach = row[0]

    # Знайдемо subtask
    subtask = get_subtask_full(attach['subtask_id'])
    if not subtask:
        flash("Підзавдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    # Перевіримо права
    if not user_can_delete_file(attach, subtask):
        flash("У вас немає прав видалити цей файл.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask['id']))

    # видаляємо з диску
    full_path = os.path.join(current_app.config['BASE_DIR'], attach['file_path'])
    if os.path.exists(full_path):
        os.remove(full_path)

    # видаляємо з БД
    execute_non_select("DELETE FROM attachments WHERE id=%s", (attachment_id,))
    flash("Файл видалено.")
    return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask['id']))

################################################################################
# РЕДАГУВАННЯ ПІДЗАВДАННЯ
################################################################################
@subtasks_bp.route('/subtask/<int:subtask_id>/edit', methods=['GET', 'POST'])
def edit_subtask(subtask_id):
    """
    Редагування підзавдання (другий ярус): назва, дедлайн, статус, assigned_role, assigned_user.
    Лише для Адміністратора або координатора проєкту.
    """
    if 'user_id' not in session:
        flash("Авторизуйтесь.")
        return redirect(url_for('auth_bp.login'))

    # Знайдемо subtask
    subtask = get_subtask_full(subtask_id)
    if not subtask:
        flash("Підзавдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))

    # Визначимо project_id
    row_ptask = execute_query(
        "SELECT project_id FROM project_tasks WHERE id=%s",
        (subtask['project_task_id'],)
    )
    if not row_ptask:
        flash("Верхнє завдання не знайдено.")
        return redirect(url_for('projects_bp.projects'))
    project_id = row_ptask[0]['project_id']

    # Перевірка прав
    if not (is_admin() or user_is_coordinator_of(project_id)):
        flash("У вас немає прав для редагування цього підзавдання.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_deadline = request.form.get('deadline')
        new_status = request.form.get('status')
        new_assigned_role = request.form.get('assigned_role')
        new_assigned_user = request.form.get('assigned_user')

        upd_q = """
            UPDATE subtasks
            SET name=%s,
                deadline=%s,
                status=%s,
                assigned_role=%s,
                assigned_user=%s
            WHERE id=%s
        """
        execute_non_select(upd_q, (
            new_name, new_deadline, new_status, new_assigned_role, new_assigned_user, subtask_id
        ))
        flash("Підзавдання оновлено.")
        return redirect(url_for('subtasks_bp.view_subtask', subtask_id=subtask_id))

    # Якщо GET
    subtask_statuses = ["В черзі", "В роботі", "Прострочено", "Виконано"]
    translator_role_id = get_role_id_by_name("Перекладач")
    worker_role_id = get_role_id_by_name("Працівник")

    translator_users = execute_query("SELECT id, username FROM users WHERE role_id=%s", (translator_role_id,))
    worker_users = execute_query("SELECT id, username FROM users WHERE role_id=%s", (worker_role_id,))

    return render_template(
        'edit_subtask.html',
        subtask=subtask,
        subtask_statuses=subtask_statuses,
        translator_role_id=translator_role_id,
        worker_role_id=worker_role_id,
        translator_users=translator_users,
        worker_users=worker_users
    )