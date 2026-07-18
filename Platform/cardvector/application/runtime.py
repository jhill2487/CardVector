from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, RLock
from typing import Any, Callable, Mapping
from uuid import uuid4


class ApplicationCancelled(RuntimeError):
    """Raised when an application operation observes cancellation."""


class CancellationToken:
    def __init__(self) -> None:
        self._event = Event()
        self._reason = ""
        self._lock = RLock()

    def cancel(self, reason: str = "") -> None:
        with self._lock:
            self._reason = str(reason or "")
            self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        with self._lock:
            return self._reason

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise ApplicationCancelled(self.reason or "Application operation canceled.")


@dataclass(frozen=True)
class ProgressUpdate:
    stage: str
    current: int | None = None
    total: int | None = None
    message: str = ""
    execution_id: str = ""


@dataclass(frozen=True)
class ApplicationEvent:
    name: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    execution_id: str = ""


class ProgressReporter:
    def __init__(self) -> None:
        self._listeners: list[Callable[[ProgressUpdate], None]] = []
        self._lock = RLock()

    def subscribe(self, listener: Callable[[ProgressUpdate], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    def publish(self, update: ProgressUpdate) -> None:
        with self._lock:
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(update)


class EventPublisher:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[ApplicationEvent], None]]] = {}
        self._lock = RLock()

    def subscribe(
        self,
        event_name: str,
        listener: Callable[[ApplicationEvent], None],
    ) -> Callable[[], None]:
        with self._lock:
            self._listeners.setdefault(event_name, []).append(listener)

        def unsubscribe() -> None:
            with self._lock:
                listeners = self._listeners.get(event_name, [])
                if listener in listeners:
                    listeners.remove(listener)

        return unsubscribe

    def publish(self, event: ApplicationEvent) -> None:
        with self._lock:
            listeners = tuple(self._listeners.get(event.name, ()))
        for listener in listeners:
            listener(event)


@dataclass
class ExecutionContext:
    execution_id: str
    cancellation: CancellationToken
    progress: ProgressReporter
    events: EventPublisher
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        execution_id: str | None = None,
        cancellation: CancellationToken | None = None,
        progress: ProgressReporter | None = None,
        events: EventPublisher | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "ExecutionContext":
        return cls(
            execution_id=execution_id or str(uuid4()),
            cancellation=cancellation or CancellationToken(),
            progress=progress or ProgressReporter(),
            events=events or EventPublisher(),
            metadata=dict(metadata or {}),
        )

    def report(
        self,
        stage: str,
        *,
        current: int | None = None,
        total: int | None = None,
        message: str = "",
    ) -> None:
        self.progress.publish(
            ProgressUpdate(
                stage=stage,
                current=current,
                total=total,
                message=message,
                execution_id=self.execution_id,
            )
        )

    def publish(self, name: str, **payload: Any) -> None:
        self.events.publish(
            ApplicationEvent(
                name=name,
                payload=payload,
                execution_id=self.execution_id,
            )
        )


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any, *, replace: bool = False) -> Any:
        key = str(name).strip()
        if not key:
            raise ValueError("Service name is required.")
        if key in self._services and not replace:
            raise KeyError(f"Service already registered: {key}")
        self._services[key] = service
        return service

    def resolve(self, name: str, expected_type: type | None = None) -> Any:
        key = str(name).strip()
        if key not in self._services:
            raise KeyError(f"Service is not registered: {key}")
        service = self._services[key]
        if expected_type is not None and not isinstance(service, expected_type):
            raise TypeError(f"Service {key} is not a {expected_type.__name__}.")
        return service

    def contains(self, name: str) -> bool:
        return str(name).strip() in self._services


@dataclass(frozen=True)
class Command:
    name: str
    payload: Mapping[str, Any] = field(default_factory=dict)


class CommandDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[Command, ExecutionContext], Any]] = {}

    def register(
        self,
        command_name: str,
        handler: Callable[[Command, ExecutionContext], Any],
        *,
        replace: bool = False,
    ) -> None:
        key = str(command_name).strip()
        if not key:
            raise ValueError("Command name is required.")
        if key in self._handlers and not replace:
            raise KeyError(f"Command handler already registered: {key}")
        self._handlers[key] = handler

    def dispatch(
        self,
        command: Command,
        context: ExecutionContext | None = None,
    ) -> Any:
        name = str(command.name).strip()
        if name not in self._handlers:
            raise KeyError(f"Command handler is not registered: {name}")
        execution = context or ExecutionContext.create()
        execution.cancellation.raise_if_cancelled()
        return self._handlers[name](command, execution)


class ApplicationRuntime:
    """Composition-neutral application services used by current and future UIs."""

    def __init__(
        self,
        *,
        services: ServiceRegistry | None = None,
        commands: CommandDispatcher | None = None,
        events: EventPublisher | None = None,
        progress: ProgressReporter | None = None,
    ) -> None:
        self.services = services or ServiceRegistry()
        self.commands = commands or CommandDispatcher()
        self.events = events or EventPublisher()
        self.progress = progress or ProgressReporter()

    def create_execution_context(
        self,
        *,
        execution_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ExecutionContext:
        return ExecutionContext.create(
            execution_id=execution_id,
            progress=self.progress,
            events=self.events,
            metadata=metadata,
        )
