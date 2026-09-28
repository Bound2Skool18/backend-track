import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StrictBool, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException


app = FastAPI(title="Task API", version="1.0")
DB_PATH = Path(__file__).resolve().with_name("tasks.db")

@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    messages = []

    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        messages.append(f"{location}: {error['msg']}")

    return JSONResponse(
        status_code=400,
        content={"error": "; ".join(messages)},
    )

@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers=exc.headers,
    )

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        with conn:
            yield conn
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        existing_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if existing_count == 0:
            conn.execute(
                "INSERT INTO tasks (title, done) VALUES (?, ?), (?, ?), (?, ?)",
                (
                    "Learn FastAPI",
                    0,
                    "Build a CRUD API",
                    0,
                    "Write the README",
                    1,
                ),
            )


init_db()


@app.get("/", summary="Describe the API")
async def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks")
async def list_tasks(
    done: bool | None = Query(default=None), search: str | None = Query(default=None)
):
    with get_connection() as conn:
        query = "SELECT id, title, done FROM tasks"
        params = []

        if done is not None:
            query += " WHERE done = ?"
            params.append(1 if done else 0)

        if search is not None:
            if done is None:
                query += " WHERE"
            else:
                query += " AND"
            query += " LOWER(title) LIKE ?"
            params.append(f"%{search.lower()}%")

        rows = conn.execute(query, params).fetchall()

    tasks = [dict(row) for row in rows]
    for task in tasks:
        task["done"] = bool(task["done"])
    return tasks


@app.get("/tasks/{task_id}", summary="Get one task")
async def get_task(task_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    if row is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )

    task = dict(row)
    task["done"] = bool(task["done"])
    return task


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Title cannot be empty")

        return value


@app.post("/tasks", status_code=201, summary="Create a task")
async def create_task(task_input: TaskCreate):
    title = task_input.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (title, 0),
        )
        task_id = cursor.lastrowid

    new_task = {"id": task_id, "title": title, "done": False}
    return new_task


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    done: StrictBool | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("Title must be a non-empty string")

        return value.strip()

    @field_validator("done")
    @classmethod
    def validate_done(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("Done must be true or false")

        return value


@app.put("/tasks/{task_id}", summary="Replace task fields")
async def update_task(task_id: int, task_input: TaskUpdate):
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        changes = task_input.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(
                status_code=400, detail="Provide a valid title or done value"
            )

        if "title" in changes:
            cleaned_title = changes["title"].strip()
            if not cleaned_title:
                raise HTTPException(
                    status_code=400, detail="Provide a valid title or done value"
                )
            changes["title"] = cleaned_title

        if "title" in changes or "done" in changes:
            update_fields = []
            values = []
            if "title" in changes:
                update_fields.append("title = ?")
                values.append(changes["title"])
            if "done" in changes:
                update_fields.append("done = ?")
                values.append(1 if changes["done"] else 0)

            values.append(task_id)
            conn.execute(
                f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?",
                values,
            )

        row = conn.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    task = dict(row)
    task["done"] = bool(task["done"])
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
async def delete_task(task_id: int):
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    return None
