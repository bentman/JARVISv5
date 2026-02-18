from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from backend.config.settings import Settings
from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager


app = FastAPI(title="JARVISv5 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    task_id: str | None = None
    user_input: str = Field(
        ...,
        validation_alias=AliasChoices("user_input", "input"),
    )


def _build_memory_manager(settings: Settings) -> MemoryManager:
    data_root = Path(settings.DATA_PATH)
    return MemoryManager(
        episodic_db_path=str(data_root / "episodic" / "trace.db"),
        working_base_path=str(data_root / "working_state"),
        working_archive_path=str(data_root / "archives"),
        semantic_db_path=str(data_root / "semantic" / "metadata.db"),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "JARVISv5-backend"}


@app.post("/task")
def create_task(request: TaskRequest) -> dict[str, str]:
    settings = Settings()
    memory = _build_memory_manager(settings)

    if request.task_id is not None and memory.get_task_state(request.task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")

    service = ControllerService(memory_manager=memory)
    result = service.run(user_input=request.user_input, task_id=request.task_id)
    context = result.get("context", {})

    return {
        "task_id": str(result.get("task_id", "")),
        "final_state": str(result.get("final_state", "")),
        "llm_output": str(context.get("llm_output", "")),
    }


@app.get("/task/{task_id}")
def get_task(task_id: str) -> dict:
    settings = Settings()
    memory = _build_memory_manager(settings)
    task_state = memory.get_task_state(task_id)
    if task_state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_state
