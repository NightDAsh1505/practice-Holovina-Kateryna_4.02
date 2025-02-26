# app/routes/projects.py
from flask import render_template, redirect, url_for, request, flash, session
from . import projects_bp
from ..db import execute_query, execute_non_select
from ..helpers import is_admin, user_is_coordinator_of, get_coordinator_for_project, get_role
import psycopg2


@projects_bp.route('/projects', methods=['GET'])
def projects():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))
    user_id = session['user_id']
    role = get_role(user_id)

    coordinator_id = request.args.get('coordinator')
    status = request.args.get('status')
    sort = request.args.get('sort')


    if role in ['Перекладач', 'Працівник']:

        base_query = """
          SELECT DISTINCT p.* 
          FROM projects p
          JOIN project_tasks pt ON pt.project_id = p.id
          JOIN subtasks st ON st.project_task_id = pt.id
          WHERE st.assigned_user = %s
        """
        params = [user_id]
    else:
        base_query = """SELECT p.* FROM projects p WHERE 1=1"""
        params = []

    if coordinator_id:
        base_query += " AND p.coordinator_id = %s"
        params.append(coordinator_id)

    if status:
        base_query += " AND p.status = %s"
        params.append(status)

    if sort == 'name_asc':
        base_query += " ORDER BY p.name ASC"
    elif sort == 'name_desc':
        base_query += " ORDER BY p.name DESC"
    elif sort == 'start_date_asc':
        base_query += " ORDER BY p.start_date ASC"
    elif sort == 'start_date_desc':
        base_query += " ORDER BY p.start_date DESC"


    data = execute_query(base_query, tuple(params))

    for p in data:
        p['coordinator'] = get_coordinator_for_project(p['id'])

    coords = execute_query("SELECT id, username FROM users WHERE role_id=2")

    project_statuses = ["В черзі", "Перекладається", "Заморожено", "Завершено"]

    return render_template(
        'projects.html',
        projects=data,
        coords=coords,
        project_statuses=project_statuses
    )


@projects_bp.route('/projects/create', methods=['GET', 'POST'])
def create_project():
    if not is_admin():
        flash("У вас немає прав для створення проєктів.")
        return redirect(url_for('projects_bp.projects'))

    if request.method == 'POST':
        name = request.form.get('name')
        coordinator_id = request.form.get('coordinator_id')  # only role_id=2
        start_date = request.form.get('start_date')
        status = request.form.get('status')

        insert_q = """
            INSERT INTO projects (name, coordinator_id, start_date, status)
            VALUES (%s, %s, %s, %s)
        """
        execute_non_select(insert_q, (name, coordinator_id, start_date, status))
        flash("Проєкт успішно створено!")
        return redirect(url_for('projects_bp.projects'))

    # Вибираємо лише користувачів-координаторів:
    users = execute_query("SELECT id, username FROM users WHERE role_id=2")
    return render_template('create_project.html', users=users)


@projects_bp.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    if not is_admin():
        flash("У вас немає прав для видалення проєктів.")
        return redirect(url_for('projects_bp.projects'))

    execute_non_select("DELETE FROM projects WHERE id=%s", (project_id,))
    flash("Проєкт видалено.")
    return redirect(url_for('projects_bp.projects'))


@projects_bp.route('/project/<int:project_id>')
def project_detail(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))

    row = execute_query("SELECT * FROM projects WHERE id=%s", (project_id,))
    if not row:
        flash("Проєкт не знайдено.")
        return redirect(url_for('projects_bp.projects'))
    project = row[0]
    project['coordinator'] = get_coordinator_for_project(project_id)

    ptasks = execute_query("SELECT * FROM project_tasks WHERE project_id=%s", (project_id,))

    return render_template('project_detail.html',
                           project_id=project_id,
                           project=project,
                           ptasks=ptasks)


@projects_bp.route('/project/<int:project_id>/create_project_task', methods=['GET', 'POST'])
def create_project_task(project_id):
    from ..helpers import is_admin, user_is_coordinator_of

    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))

    if not (is_admin() or user_is_coordinator_of(project_id)):
        flash("У вас немає прав для створення завдання у цьому проєкті.")
        return redirect(url_for('projects_bp.project_detail', project_id=project_id))

    project_data = execute_query("SELECT * FROM projects WHERE id=%s", (project_id,))
    if not project_data:
        flash("Проєкт не знайдено.")
        return redirect(url_for('projects_bp.projects'))
    project = project_data[0]

    if request.method == 'POST':
        name = request.form.get('name')
        deadline = request.form.get('deadline')
        status = request.form.get('status')

        insert_q = """
            INSERT INTO project_tasks (project_id, name, deadline, status)
            VALUES (%s, %s, %s, %s)
        """
        execute_non_select(insert_q, (project_id, name, deadline, status))
        flash("Верхнє завдання створено.")
        return redirect(url_for('projects_bp.project_detail', project_id=project_id))

    return render_template('create_project_task.html', project=project)


@projects_bp.route('/project/<int:project_id>/project_task/<int:ptask_id>/delete', methods=['POST'])
def delete_project_task(project_id, ptask_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))

    if not (is_admin() or user_is_coordinator_of(project_id)):
        flash("У вас немає прав для видалення завдання в цьому проєкті.")
        return redirect(url_for('projects_bp.project_detail', project_id=project_id))

    execute_non_select("DELETE FROM project_tasks WHERE id=%s", (ptask_id,))
    flash("Верхнє завдання видалено.")
    return redirect(url_for('projects_bp.project_detail', project_id=project_id))


@projects_bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    if not is_admin():
        flash("У вас немає прав для редагування проєктів.")
        return redirect(url_for('projects_bp.projects'))

    row = execute_query("SELECT * FROM projects WHERE id=%s", (project_id,))
    if not row:
        flash("Проєкт не знайдено.")
        return redirect(url_for('projects_bp.projects'))
    project = row[0]

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_coordinator_id = request.form.get('coordinator_id')
        new_status = request.form.get('status')
        upd_q = """
            UPDATE projects
            SET name=%s,
                coordinator_id=%s,
                status=%s
            WHERE id=%s
        """
        execute_non_select(upd_q, (new_name, new_coordinator_id, new_status, project_id))
        flash("Проєкт успішно оновлено.")
        return redirect(url_for('projects_bp.project_detail', project_id=project_id))

    coords = execute_query("SELECT id, username FROM users WHERE role_id=2")
    return render_template('edit_project.html', project=project, coords=coords)


@projects_bp.route('/project/<int:project_id>/project_task/<int:ptask_id>/edit', methods=['GET', 'POST'])
def edit_project_task(project_id, ptask_id):
    if 'user_id' not in session:
        flash("Авторизуйтесь.")
        return redirect(url_for('auth_bp.login'))

    from ..helpers import is_admin, user_is_coordinator_of

    if not (is_admin() or user_is_coordinator_of(project_id)):
        flash("У вас немає прав для редагування завдання у цьому проєкті.")
        return redirect(url_for('projects_bp.project_detail', project_id=project_id))

    row = execute_query("SELECT * FROM project_tasks WHERE id=%s AND project_id=%s", (ptask_id, project_id))
    if not row:
        flash("Не знайдено верхнє завдання.")
        return redirect(url_for('projects_bp.project_detail', project_id=project_id))

    task = row[0]

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_deadline = request.form.get('deadline')
        new_status = request.form.get('status')

        upd_q = """
            UPDATE project_tasks
            SET name=%s, deadline=%s, status=%s
            WHERE id=%s
        """
        execute_non_select(upd_q, (new_name, new_deadline, new_status, ptask_id))
        flash("Верхнє завдання оновлено.")
        return redirect(url_for('subtasks_bp.project_task_detail', project_id=project_id, ptask_id=ptask_id))

    return render_template('edit_task.html', task=task, project_id=project_id)
