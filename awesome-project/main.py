from fastapi import FastAPI, HTTPException
#from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi import Query 

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


tasks = [
    {"id": 1, "title": "Learn FastAPI", "done": False},
    {"id": 2, "title": "Build a CRUD API", "done": False},
    {"id": 3, "title": "Learn FastAPI", "done": True},
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


class TaskUpdate(BaseModel):
    title: str | None = None 
    done: bool | None = None 

@app.put("/tasks/{task_id}", summary="Replace task fields")
async def update_task(task_id: int, task_input: TaskUpdate):
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    changes = task_input.model_dump(exclude_unset=True)
    if not changes or ("title" in changes and not changes ["title"].strip()): 
        raise HTTPException(status_code=400, detail="Prove a valid title or done value")
    if "title" in changes: 
        changes["title"] = changes["title"].strip()
        task.update(changes)
        return task

@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
async def delete_task(task_id: int): 
    task_index = next(
        (index for index, task in enumerate(tasks) if 
        task["id"] == task_id), 
        None,
    )
    if task_index is None:
        raise HTTPException(status_code=404, detail=f"Task{task_id} not found")
    tasks.pop(task_index)

@app.get("/tasks", summary="List and filter tasks")
async def list_tasks( 
    done: bool | None = Query(default=None),
    search: str | None = Query(default=None),
):
    result = tasks 
    if done is not None: 
        result = [task for task in result if task ["done"] == done]
    if search:
        result = [task for task in result if search.lower() in task["title"].lower()]
        return result


