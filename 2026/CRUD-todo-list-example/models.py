import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todo.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.commit()
    conn.close()


def create_task(title, description=""):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, description) VALUES (?, ?)",
        (title, description),
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id


def get_all_tasks():
    conn = get_connection()
    tasks = conn.execute(
        "SELECT id, title, description, completed, created_at FROM tasks ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in tasks]


def update_task(task_id, title, description, completed):
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET title = ?, description = ?, completed = ? WHERE id = ?",
        (title, description, int(completed), task_id),
    )
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
