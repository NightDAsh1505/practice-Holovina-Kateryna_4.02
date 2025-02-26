# app/db.py
import psycopg2
from psycopg2.extras import RealDictCursor

DB_NAME = "scanlation_project_management"
DB_USER = "postgres"
DB_PASSWORD = "DoesMe333111!"
DB_HOST = "localhost"
DB_PORT = "5432"

def get_connection():
    """Підключення до бази даних."""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def execute_query(query, params=None):
    """Універсальний метод виконання запитів."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return cursor.fetchall()

def execute_non_select(query, params=None):
    """
    Метод для INSERT/UPDATE/DELETE запитів,
    які не повертають результат у вигляді рядків.
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
        conn.commit()

