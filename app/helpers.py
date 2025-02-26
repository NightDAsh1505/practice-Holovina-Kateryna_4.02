# app/helpers.py
from flask import session, current_app
import os
from .db import execute_query

def get_role(user_id):
    if not user_id:
        return None
    query = """
        SELECT r.name 
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.id = %s
    """
    row = execute_query(query, (user_id,))
    if row:
        return row[0]['name']
    return None

def get_role_id_by_name(role_name):
    query = "SELECT id FROM roles WHERE name = %s"
    row = execute_query(query, (role_name,))
    if row:
        return row[0]['id']
    return None

def get_role_name(role_id):
    if not role_id:
        return None
    query = "SELECT name FROM roles WHERE id=%s"
    data = execute_query(query, (role_id,))
    return data[0]['name'] if data else None

def get_username(user_id):
    if not user_id:
        return None
    query = "SELECT username FROM users WHERE id=%s"
    data = execute_query(query, (user_id,))
    return data[0]['username'] if data else None

def get_coordinator_for_project(project_id):
    query = """
        SELECT u.id, u.username, u.email
        FROM projects p
        JOIN users u ON p.coordinator_id = u.id
        WHERE p.id = %s
    """
    res = execute_query(query, (project_id,))
    return res[0] if res else None

def is_admin():
    return session.get('role') == 'Адміністратор'

def user_is_coordinator_of(project_id):
    if 'user_id' not in session:
        return False
    user_id = session['user_id']
    coord = get_coordinator_for_project(project_id)
    if not coord:
        return False
    return coord['id'] == user_id

# ----------------------------------------------------------------------
# Логіка для завантаження файлів
# ----------------------------------------------------------------------

def allowed_file(filename):
    """
    Перевірка, чи розширення файлу допустиме
    (записані у app.config['ALLOWED_EXTENSIONS']).
    """
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    # Отримаємо сет/словник дозволених з config
    allowed_exts = current_app.config.get('ALLOWED_EXTENSIONS', {'doc','docx','pdf','jpg','jpeg','png','txt'})
    return ext in allowed_exts

# ----------------------------------------------------------------------
# Хелпери для Subtask
# ----------------------------------------------------------------------

def get_subtask_full(subtask_id):
    """
    Витягнути Subtask + під'єднати назви ролі та користувача.
    """
    q = """
        SELECT s.*,
               r.name as assigned_role_name,
               u.username as assigned_user_name
        FROM subtasks s
        LEFT JOIN roles r ON s.assigned_role = r.id
        LEFT JOIN users u ON s.assigned_user = u.id
        WHERE s.id=%s
    """
    row = execute_query(q, (subtask_id,))
    if row:
        return row[0]
    return None

def user_can_view_subtask(subtask):
    """
    Перевіряє, чи поточний користувач може бачити це підзавдання.
    Логіка:
      - Якщо користувач Адміністратор -> ок
      - Якщо координатор проекту -> ок
      - Якщо assigned_user == this user -> ок
    Інакше: ні.
    """
    user_id = session.get('user_id')
    if not user_id:
        return False
    role = get_role(user_id)
    # Знайдемо project_id через project_task
    ptask_id = subtask['project_task_id']
    prow = execute_query("SELECT project_id FROM project_tasks WHERE id=%s", (ptask_id,))
    if not prow:
        return False
    project_id = prow[0]['project_id']

    if role == 'Адміністратор':
        return True
    if role == 'Координатор' and user_is_coordinator_of(project_id):
        return True
    # Якщо assigned_user:
    if subtask['assigned_user'] == user_id:
        return True
    return False

def user_can_upload_subtask(subtask):
    """
    Хто може завантажувати файли:
     - Адміністратор,
     - Координатор проекту,
     - assigned_user цього subtask.
    """
    user_id = session.get('user_id')
    if not user_id:
        return False
    role = get_role(user_id)
    # project_id
    ptask_id = subtask['project_task_id']
    prow = execute_query("SELECT project_id FROM project_tasks WHERE id=%s", (ptask_id,))
    if not prow:
        return False
    project_id = prow[0]['project_id']

    if role == 'Адміністратор':
        return True
    if role == 'Координатор' and user_is_coordinator_of(project_id):
        return True
    if subtask['assigned_user'] == user_id:
        return True
    return False

def user_can_download_file(subtask):
    """
    Логіка така сама, як user_can_view_subtask,
    бо якщо він бачить subtask, він може й скачати файл.
    """
    return user_can_view_subtask(subtask)

def user_can_delete_file(attach, subtask):
    """
    Хто може видалити файл:
      - Адмін,
      - Координатор проєкту,
      - Або uploader сам.
    """
    user_id = session.get('user_id')
    if not user_id:
        return False
    role = get_role(user_id)
    # дізнаємося project_id
    ptask_id = subtask['project_task_id']
    prow = execute_query("SELECT project_id FROM project_tasks WHERE id=%s", (ptask_id,))
    if not prow:
        return False
    project_id = prow[0]['project_id']

    if role == 'Адміністратор':
        return True
    if role == 'Координатор' and user_is_coordinator_of(project_id):
        return True
    if attach['uploader_id'] == user_id:
        return True
    return False


def user_can_comment(subtask):
    """
    Хто може лишати коментар?
    - Адміністратор
    - Координатор проєкту
    - assigned_user (перекладач/працівник)
    """
    if 'user_id' not in session:
        return False
    user_id = session['user_id']
    role = get_role(user_id)

    # Знайдемо project_id через project_tasks
    row_ptask = execute_query("SELECT project_id FROM project_tasks WHERE id=%s",
                              (subtask['project_task_id'],))
    if not row_ptask:
        return False
    project_id = row_ptask[0]['project_id']

    if role == 'Адміністратор':
        return True
    if role == 'Координатор' and user_is_coordinator_of(project_id):
        return True
    if subtask['assigned_user'] == user_id:
        return True
    return False

def user_can_edit_comment(comment_row, subtask):
    """
    Хто може редагувати/видаляти коментар?
    - Автор коментаря
    - Адмін
    - Координатор проекту
    """
    if 'user_id' not in session:
        return False
    user_id = session['user_id']
    if comment_row['user_id'] == user_id:
        return True
    # Якщо адмін:
    role = get_role(user_id)
    if role == 'Адміністратор':
        return True
    # Якщо координатор цього проекту:
    row_ptask = execute_query("SELECT project_id FROM project_tasks WHERE id=%s",
                              (subtask['project_task_id'],))
    if row_ptask:
        project_id = row_ptask[0]['project_id']
        if role == 'Координатор' and user_is_coordinator_of(project_id):
            return True
    return False
