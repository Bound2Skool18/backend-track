import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env before starting."
        )
    return value


@contextmanager
def get_connection():
    with psycopg.connect(database_url(), row_factory=dict_row) as connection:
        yield connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )

        count = connection.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()
        if count["count"] == 0:
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    [
                        ("Learn FastAPI", False),
                        ("Build a CRUD API", False),
                        ("Write the README", True),
                    ],
                )


def database_is_healthy() -> bool:
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


def list_tasks(done: bool | None = None, search: str | None = None) -> list[dict]:
    query = "SELECT id, title, done FROM tasks"
    clauses = []
    params = []

    if done is not None:
        clauses.append("done = %s")
        params.append(done)

    if search is not None:
        clauses.append("title ILIKE %s")
        params.append(f"%{search}%")

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY id"

    with get_connection() as connection:
        return list(connection.execute(query, params).fetchall())


def get_task(task_id: int) -> dict | None:
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = %s",
            (task_id,),
        ).fetchone()


def create_task(title: str) -> dict:
    with get_connection() as connection:
        return connection.execute(
            """
            INSERT INTO tasks (title, done)
            VALUES (%s, %s)
            RETURNING id, title, done
            """,
            (title, False),
        ).fetchone()


def update_task(task_id: int, changes: dict) -> dict | None:
    with get_connection() as connection:
        return connection.execute(
            """
            UPDATE tasks
            SET title = COALESCE(%s, title), done = COALESCE(%s, done)
            WHERE id = %s
            RETURNING id, title, done
            """,
            (changes.get("title"), changes.get("done"), task_id),
        ).fetchone()


def delete_task(task_id: int) -> bool:
    with get_connection() as connection:
        deleted = connection.execute(
            "DELETE FROM tasks WHERE id = %s RETURNING id",
            (task_id,),
        ).fetchone()
    return deleted is not None
