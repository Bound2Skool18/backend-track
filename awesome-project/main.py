from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StrictBool, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

import repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository.init_db()
    yield


app = FastAPI(title="Task API", version="1.0", lifespan=lifespan)


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


@app.get("/", summary="Describe the API")
async def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", summary="Check the API and database")
async def health():
    if not repository.database_is_healthy():
        raise HTTPException(status_code=503, detail="Database unavailable")

    return {"status": "ok", "db": "ok"}


@app.get("/tasks", summary="List all tasks")
async def list_tasks(
    done: bool | None = Query(default=None), search: str | None = Query(default=None)
):
    return repository.list_tasks(done=done, search=search)


@app.get("/tasks/{task_id}", summary="Get one task")
async def get_task(task_id: int):
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

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
    return repository.create_task(task_input.title)


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


@app.put("/tasks/{task_id}", summary="Update task fields")
async def update_task(task_id: int, task_input: TaskUpdate):
    if repository.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")

    changes = task_input.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=400, detail="Provide a valid title or done value"
        )

    task = repository.update_task(task_id, changes)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
async def delete_task(task_id: int):
    if not repository.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    return None
