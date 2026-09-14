# Task API Project Instructions

This guide translates **W2 - Build your first CRUD API** into the remaining work for this FastAPI project. Build the stages in order, test after each stage, and make one Git commit per completed stage.

## Current Starting Point

The project already has:

- FastAPI configured in `pyproject.toml`
- `GET /`, returning the Task API name, version, and task resource
- `GET /health`, returning the current health information
- FastAPI's interactive documentation at `http://localhost:8000/docs`

Before continuing, align Stage 1 with the assignment: change `GET /health` to return exactly `{"status": "ok"}`. The current starter response is useful, but it is not the PDF's required contract.

Run the server from this folder with:

```bash
uv run fastapi dev main.py
```

The API is in-memory, so tasks reset whenever the server restarts. That is expected for this assignment.

## What You Need to Build

| Operation | Method and path | Success | Missing or invalid input |
|---|---|---:|---|
| List tasks | `GET /tasks` | `200` | N/A |
| Get one task | `GET /tasks/{id}` | `200` | `404` with JSON error |
| Create task | `POST /tasks` | `201` | `400` with JSON error |
| Update task | `PUT /tasks/{id}` | `200` | `400` or `404` |
| Delete task | `DELETE /tasks/{id}` | `204`, empty body | `404` |

Every task must have this shape:

```json
{
  "id": 1,
  "title": "Buy milk",
  "done": false
}
```

## Build in Stages

### Stage 2: Read Tasks

Add three example tasks near the top of `main.py`. Use a list of dictionaries first; this keeps the focus on HTTP and CRUD.

```python
tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Write the README", "done": True},
]


@app.get("/tasks", summary="List all tasks")
async def list_tasks():
    return tasks


@app.get("/tasks/{task_id}", summary="Get one task")
async def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
```

Add the import used by the error path:

```python
from fastapi import FastAPI, HTTPException
```

FastAPI serializes the exception as `{"detail": "..."}`. If the assignment requires the exact `{"error": "..."}` key, return it with `JSONResponse` instead:

```python
from fastapi.responses import JSONResponse

return JSONResponse(
    status_code=404,
    content={"error": f"Task {task_id} not found"},
)
```

Checkpoint:

```bash
curl -i http://localhost:8000/tasks
curl -i http://localhost:8000/tasks/1
curl -i http://localhost:8000/tasks/99
```

### Stage 3: Create and Validate

Use a Pydantic request model so FastAPI parses JSON and validates the title.

```python
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str


@app.post("/tasks", status_code=201, summary="Create a task")
async def create_task(task_input: TaskCreate):
    title = task_input.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    new_task = {
        "id": max((task["id"] for task in tasks), default=0) + 1,
        "title": title,
        "done": False,
    }
    tasks.append(new_task)
    return new_task
```

Checkpoint:

```bash
curl -i -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Buy milk"}'

curl -i -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{}'

curl -i -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"   "}'
```

The valid request should return `201`. Empty or missing titles must be rejected. Depending on how strictly you match the assignment, malformed JSON/model validation may naturally return FastAPI's `422`; your own empty-title business rule should return `400`.

### Stage 4: Update and Delete

The assignment allows updating `title`, `done`, or both. A second model makes both fields optional while still validating their types.

```python
class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


@app.put("/tasks/{task_id}", summary="Replace task fields")
async def update_task(task_id: int, task_input: TaskUpdate):
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    changes = task_input.model_dump(exclude_unset=True)
    if not changes or ("title" in changes and not changes["title"].strip()):
        raise HTTPException(status_code=400, detail="Provide a valid title or done value")
    if "title" in changes:
        changes["title"] = changes["title"].strip()
    task.update(changes)
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
async def delete_task(task_id: int):
    task_index = next(
        (index for index, task in enumerate(tasks) if task["id"] == task_id),
        None,
    )
    if task_index is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    tasks.pop(task_index)
```

Do not return a body from a `204` endpoint.

Checkpoint:

```bash
curl -i -X PUT http://localhost:8000/tasks/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Learn HTTP","done":true}'

curl -i -X DELETE http://localhost:8000/tasks/1
curl -i http://localhost:8000/tasks/99
```

### Stage 5: Verify Swagger UI

Open `http://localhost:8000/docs`. Confirm that all five task routes are listed. Use **Try it out** to create, list, update, and delete a task. Add `summary` or `description` text to each route so the generated documentation is understandable. Capture a screenshot for the README.

### Stage 6: Publish the Work

Create a public GitHub repository and include:

1. A short explanation of the Task API.
2. Installation and one documented run command.
3. An endpoint table.
4. One pasted `curl -i` response showing headers and status.
5. A Swagger UI screenshot.
6. A note explaining that in-memory tasks disappear after a restart.

Suggested commit sequence:

```bash
git init
git add .
git commit -m "Stage 0: hello server"
git commit -am "Stage 1: root and health endpoints"
git commit -am "Stage 2: read endpoints with 404"
git commit -am "Stage 3: create with validation"
git commit -am "Stage 4: full CRUD"
git commit -am "Stage 5: Swagger UI"
git add README.md
git commit -m "Stage 6: publish and docs"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```

Only use `git commit -am` after files are already tracked. Check `git status` before each commit.

## Optional Extensions

After the required API works, choose one small extension:

```python
from fastapi import Query


@app.get("/tasks", summary="List and filter tasks")
async def list_tasks(
    done: bool | None = Query(default=None),
    search: str | None = Query(default=None),
):
    result = tasks
    if done is not None:
        result = [task for task in result if task["done"] == done]
    if search:
        result = [task for task in result if search.lower() in task["title"].lower()]
    return result
```

Other options from the assignment are `GET /stats` and `POST /reset`. Document any extra endpoint in the README and add a separate commit.

## Learning Checklist

Be able to explain these before submitting:

- Why `GET /tasks` and `POST /tasks` are different endpoints.
- The difference between a path parameter (`/tasks/3`) and a query parameter (`/tasks?done=true`).
- Why create returns `201`, delete returns `204`, and missing resources return `404`.
- How a Pydantic model turns request JSON into a validated Python object.
- Why this data disappears on restart and why a real application would use a database.
- How FastAPI generates OpenAPI JSON and Swagger UI from route definitions.

## Final Verification

Run these checks before pushing:

```bash
uv run python -m compileall main.py
uv run fastapi dev main.py
```

Then manually complete the full sequence in Swagger or curl:

1. `GET /tasks`
2. `POST /tasks` and record the new ID
3. `GET /tasks/{id}`
4. `PUT /tasks/{id}` with `done: true`
5. `DELETE /tasks/{id}`
6. `GET /tasks/{id}` and confirm `404`

The project is ready when a new reader can follow the README, start the server in under five minutes, and exercise the complete CRUD cycle.