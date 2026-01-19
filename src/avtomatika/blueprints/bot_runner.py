"""Blueprint для управления ботами через Bot Runner Worker."""

from ..blueprint import StateMachineBlueprint
from ..data_types import JobContext
from .bot_runner_validator import validate_bot_request, ValidationError


blueprint = StateMachineBlueprint("bot_runner", api_endpoint="/jobs/bot_runner")


@blueprint.state("init")
async def init_handler(context: JobContext):
    """
    Начальное состояние: валидация запроса и маршрутизация.
    
    Определяет действие (start/stop/logs/list/status) и направляет
    в соответствующее состояние.
    """
    data = context.initial_data
    
    # Валидация запроса
    try:
        validate_bot_request(data)
    except ValidationError as e:
        data["error"] = e.to_dict()
        context.actions.transition_to("validation_failed")
        return
    
    # Добавляем user_id из client если не указан
    if context.client and hasattr(context.client, 'name'):
        data.setdefault("user_id", context.client.name)
    
    # Если user_id всё ещё не указан, генерируем из job_id
    if "user_id" not in data:
        data["user_id"] = f"anonymous_{context.job_id[:8]}"
    
    action = data.get("action")
    
    if action == "start":
        context.actions.transition_to("start_bot")
    elif action == "stop":
        context.actions.transition_to("stop_bot")
    elif action == "logs":
        context.actions.transition_to("get_logs")
    elif action == "list":
        context.actions.transition_to("list_bots")
    elif action == "status":
        context.actions.transition_to("check_status")
    else:
        # Не должно произойти после валидации, но на всякий случай
        data["error"] = {"message": f"Unknown action: {action}"}
        context.actions.transition_to("failed")


@blueprint.state("start_bot")
async def start_bot_handler(context: JobContext):
    """Отправка задачи на запуск бота воркеру."""
    data = context.initial_data
    
    context.actions.dispatch_task(
        task_type="start_bot",
        params={
            "user_id": data["user_id"],
            "bot_id": data["bot_id"],
            "deployment_mode": data["deployment_mode"],
            
            # Simple режим
            "code": data.get("code"),
            "files": data.get("files"),
            "requirements": data.get("requirements", []),
            "entrypoint": data.get("entrypoint", "bot.py"),
            
            # Custom режим
            "archive": data.get("archive"),
            "archive_url": data.get("archive_url"),
            "git_repo": data.get("git_repo"),
            "git_branch": data.get("git_branch", "main"),
            "git_subdir": data.get("git_subdir"),
            
            # Image режим
            "docker_image": data.get("docker_image"),
            "registry_auth": data.get("registry_auth"),
            
            # Общие параметры
            "env_vars": data.get("env_vars", {}),
            "resource_limits": data.get("resource_limits"),
        },
        transitions={
            "success": "bot_started",
            "failure": "start_failed"
        },
        timeout_seconds=300  # 5 минут на сборку и запуск
    )


@blueprint.state("stop_bot")
async def stop_bot_handler(context: JobContext):
    """Отправка задачи на остановку бота."""
    data = context.initial_data
    
    context.actions.dispatch_task(
        task_type="stop_bot",
        params={
            "user_id": data["user_id"],
            "bot_id": data["bot_id"]
        },
        transitions={
            "success": "bot_stopped",
            "failure": "stop_failed"
        },
        timeout_seconds=30
    )


@blueprint.state("get_logs")
async def get_logs_handler(context: JobContext):
    """Отправка задачи на получение логов."""
    data = context.initial_data
    
    context.actions.dispatch_task(
        task_type="get_logs",
        params={
            "user_id": data["user_id"],
            "bot_id": data["bot_id"],
            "lines": data.get("lines", 100)
        },
        transitions={
            "success": "logs_received",
            "failure": "logs_failed"
        },
        timeout_seconds=10
    )


@blueprint.state("list_bots")
async def list_bots_handler(context: JobContext):
    """Отправка задачи на получение списка ботов."""
    data = context.initial_data
    
    context.actions.dispatch_task(
        task_type="list_bots",
        params={
            "user_id": data["user_id"]
        },
        transitions={
            "success": "list_received",
            "failure": "list_failed"
        },
        timeout_seconds=10
    )


@blueprint.state("check_status")
async def check_status_handler(context: JobContext):
    """Отправка задачи на проверку статуса бота."""
    data = context.initial_data
    
    context.actions.dispatch_task(
        task_type="check_status",
        params={
            "user_id": data["user_id"],
            "bot_id": data["bot_id"]
        },
        transitions={
            "success": "status_received",
            "failure": "status_failed"
        },
        timeout_seconds=10
    )


# ========================================
# Успешные финальные состояния
# ========================================

@blueprint.state("bot_started")
async def bot_started_handler(context: JobContext, task_result: dict | None = None):
    """Бот успешно запущен."""
    data = context.initial_data
    if task_result:
        data["result"] = task_result.get("data", {})
        data["message"] = f"Bot '{data['bot_id']}' started successfully"
    context.actions.transition_to("completed")


@blueprint.state("bot_stopped")
async def bot_stopped_handler(context: JobContext, task_result: dict | None = None):
    """Бот успешно остановлен."""
    data = context.initial_data
    if task_result:
        data["result"] = task_result.get("data", {})
        data["message"] = f"Bot '{data['bot_id']}' stopped"
    context.actions.transition_to("completed")


@blueprint.state("logs_received")
async def logs_received_handler(context: JobContext, task_result: dict | None = None):
    """Логи получены."""
    data = context.initial_data
    if task_result:
        data["result"] = task_result.get("data", {})
    context.actions.transition_to("completed")


@blueprint.state("list_received")
async def list_received_handler(context: JobContext, task_result: dict | None = None):
    """Список ботов получен."""
    data = context.initial_data
    if task_result:
        data["result"] = task_result.get("data", {})
    context.actions.transition_to("completed")


@blueprint.state("status_received")
async def status_received_handler(context: JobContext, task_result: dict | None = None):
    """Статус бота получен."""
    data = context.initial_data
    if task_result:
        data["result"] = task_result.get("data", {})
    context.actions.transition_to("completed")


# ========================================
# Состояния ошибок
# ========================================

@blueprint.state("validation_failed")
async def validation_failed_handler(context: JobContext):
    """Ошибка валидации запроса."""
    # Ошибка уже в data["error"]
    context.actions.transition_to("failed")


@blueprint.state("start_failed")
async def start_failed_handler(context: JobContext, task_result: dict | None = None):
    """Ошибка запуска бота."""
    data = context.initial_data
    if task_result:
        data["error"] = task_result.get("error", {"message": "Unknown error"})
    context.actions.transition_to("failed")


@blueprint.state("stop_failed")
async def stop_failed_handler(context: JobContext, task_result: dict | None = None):
    """Ошибка остановки бота."""
    data = context.initial_data
    if task_result:
        data["error"] = task_result.get("error", {"message": "Unknown error"})
    context.actions.transition_to("failed")


@blueprint.state("logs_failed")
async def logs_failed_handler(context: JobContext, task_result: dict | None = None):
    """Ошибка получения логов."""
    data = context.initial_data
    if task_result:
        data["error"] = task_result.get("error", {"message": "Unknown error"})
    context.actions.transition_to("failed")


@blueprint.state("list_failed")
async def list_failed_handler(context: JobContext, task_result: dict | None = None):
    """Ошибка получения списка."""
    data = context.initial_data
    if task_result:
        data["error"] = task_result.get("error", {"message": "Unknown error"})
    context.actions.transition_to("failed")


@blueprint.state("status_failed")
async def status_failed_handler(context: JobContext, task_result: dict | None = None):
    """Ошибка проверки статуса."""
    data = context.initial_data
    if task_result:
        data["error"] = task_result.get("error", {"message": "Unknown error"})
    context.actions.transition_to("failed")


# ========================================
# Финальные состояния
# ========================================

@blueprint.state("completed")
async def completed_handler(context: JobContext):
    """Финальное состояние: успех."""
    pass  # Job завершён успешно


@blueprint.state("failed")
async def failed_handler(context: JobContext):
    """Финальное состояние: ошибка."""
    pass  # Job завершён с ошибкой
