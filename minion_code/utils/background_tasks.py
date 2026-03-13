#!/usr/bin/env python3
"""Background task management for long-running bash and subagent jobs."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from secrets import token_hex
from typing import Any, Awaitable, Callable, Dict, List, Optional


TaskStatusValue = str
TaskKindValue = str


@dataclass
class TaskRecord:
    """Serializable metadata for a background task."""

    task_id: str
    kind: TaskKindValue
    title: str
    status: TaskStatusValue
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    cwd: str = ""
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    log_path: str = ""
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BackgroundTaskManager:
    """Tracks background bash processes and background subagent jobs."""

    def __init__(self, workdir: Path):
        self.workdir = workdir.resolve()
        self.tasks_dir = self.workdir / ".minion" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, TaskRecord] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._async_jobs: Dict[str, asyncio.Task] = {}
        self._load_existing_records()

    def _load_existing_records(self) -> None:
        for record_path in self.tasks_dir.glob("*.json"):
            try:
                data = json.loads(record_path.read_text(encoding="utf-8"))
                record = TaskRecord(**data)
                self._records[record.task_id] = record
            except Exception:
                continue

    def _record_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def _log_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.log"

    def _save_record(self, record: TaskRecord) -> None:
        self._records[record.task_id] = record
        self._record_path(record.task_id).write_text(
            json.dumps(record.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _create_record(
        self,
        *,
        kind: TaskKindValue,
        title: str,
        cwd: Path,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskRecord:
        task_id = token_hex(6)
        record = TaskRecord(
            task_id=task_id,
            kind=kind,
            title=title,
            status="queued",
            created_at=time.time(),
            cwd=str(cwd),
            log_path=str(self._log_path(task_id)),
            metadata=metadata or {},
        )
        self._save_record(record)
        return record

    def get_record(self, task_id: str) -> Optional[TaskRecord]:
        record = self._records.get(task_id)
        if not record:
            record_path = self._record_path(task_id)
            if record_path.exists():
                try:
                    record = TaskRecord(
                        **json.loads(record_path.read_text(encoding="utf-8"))
                    )
                    self._records[task_id] = record
                except Exception:
                    return None
        if record:
            self._refresh_record_status(record)
        return record

    def list_records(
        self, *, status: Optional[str] = None, kind: Optional[str] = None
    ) -> List[TaskRecord]:
        records = list(self._records.values())
        for record in records:
            self._refresh_record_status(record)
        if status:
            records = [record for record in records if record.status == status]
        if kind:
            records = [record for record in records if record.kind == kind]
        return sorted(records, key=lambda record: record.created_at, reverse=True)

    def _refresh_record_status(self, record: TaskRecord) -> None:
        if record.task_id in self._processes:
            process = self._processes[record.task_id]
            return_code = process.poll()
            if return_code is not None and record.status == "running":
                record.exit_code = return_code
                record.finished_at = time.time()
                if return_code == 0:
                    record.status = "completed"
                else:
                    record.status = "failed"
                    record.error = record.error or f"Process exited with code {return_code}"
                self._save_record(record)
                self._processes.pop(record.task_id, None)
        elif record.task_id in self._async_jobs:
            job = self._async_jobs[record.task_id]
            if job.done() and record.status == "running":
                if job.cancelled():
                    record.status = "cancelled"
                    record.finished_at = time.time()
                elif job.exception():
                    record.status = "failed"
                    record.finished_at = time.time()
                    record.error = str(job.exception())
                self._save_record(record)
                self._async_jobs.pop(record.task_id, None)
        elif record.kind == "bash" and record.status == "running" and record.pid:
            try:
                os.kill(record.pid, 0)
            except OSError:
                if record.finished_at is None:
                    record.finished_at = time.time()
                if record.exit_code == 0:
                    record.status = "completed"
                elif record.exit_code is not None:
                    record.status = "failed"
                self._save_record(record)

    async def start_process_task(
        self,
        *,
        command: str,
        cwd: Path,
        timeout: Optional[int],
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskRecord:
        title = title or command
        record = self._create_record(
            kind="bash",
            title=title,
            cwd=cwd,
            metadata={"command": command, "timeout": timeout, **(metadata or {})},
        )

        log_path = Path(record.log_path)
        log_handle = log_path.open("ab")
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(cwd),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        finally:
            log_handle.close()

        record.status = "running"
        record.started_at = time.time()
        record.pid = process.pid
        self._save_record(record)
        self._processes[record.task_id] = process
        self._async_jobs[record.task_id] = asyncio.create_task(
            self._monitor_process(record.task_id, process, timeout)
        )
        return record

    async def _monitor_process(
        self, task_id: str, process: subprocess.Popen, timeout: Optional[int]
    ) -> None:
        record = self._records[task_id]
        try:
            if timeout:
                try:
                    return_code = await asyncio.to_thread(process.wait, timeout)
                except subprocess.TimeoutExpired:
                    self._terminate_process(process)
                    return_code = await asyncio.to_thread(process.wait)
                    record.status = "failed"
                    record.error = f"Timed out after {timeout} seconds"
            else:
                return_code = await asyncio.to_thread(process.wait)

            if record.status == "cancelled":
                record.exit_code = return_code
                record.finished_at = time.time()
                self._save_record(record)
                return

            record.exit_code = return_code
            record.finished_at = time.time()
            if record.status != "failed":
                if return_code == 0:
                    record.status = "completed"
                else:
                    record.status = "failed"
                    record.error = record.error or f"Process exited with code {return_code}"
            self._save_record(record)
        finally:
            self._processes.pop(task_id, None)
            self._async_jobs.pop(task_id, None)

    def _terminate_process(self, process: subprocess.Popen) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception:
            try:
                process.terminate()
            except Exception:
                pass

    def _kill_process(self, process: subprocess.Popen) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    async def start_async_task(
        self,
        *,
        title: str,
        cwd: Path,
        coroutine_factory: Callable[[TaskRecord], Awaitable[str]],
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskRecord:
        record = self._create_record(
            kind="subagent",
            title=title,
            cwd=cwd,
            metadata=metadata or {},
        )
        record.status = "running"
        record.started_at = time.time()
        self._save_record(record)
        job = asyncio.create_task(
            self._run_async_task(record.task_id, coroutine_factory, timeout)
        )
        self._async_jobs[record.task_id] = job
        return record

    async def _run_async_task(
        self,
        task_id: str,
        coroutine_factory: Callable[[TaskRecord], Awaitable[str]],
        timeout: Optional[int],
    ) -> None:
        record = self._records[task_id]
        try:
            if timeout:
                result = await asyncio.wait_for(coroutine_factory(record), timeout)
            else:
                result = await coroutine_factory(record)
            record.result = result
            record.status = "completed"
        except asyncio.CancelledError:
            record.status = "cancelled"
            record.error = "Task cancelled"
            raise
        except asyncio.TimeoutError:
            record.status = "failed"
            record.error = f"Task timed out after {timeout} seconds"
            self.append_log(task_id, f"\n[error] {record.error}\n")
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            self.append_log(task_id, f"\n[error] {exc}\n")
        finally:
            record.finished_at = time.time()
            self._save_record(record)
            self._async_jobs.pop(task_id, None)

    def append_log(self, task_id: str, content: str) -> None:
        log_path = self._log_path(task_id)
        with log_path.open("a", encoding="utf-8", errors="ignore") as handle:
            handle.write(content)

    def read_output(
        self, task_id: str, *, offset: int = 0, limit: int = 8192
    ) -> Dict[str, Any]:
        record = self.get_record(task_id)
        if record is None:
            return {
                "task_id": task_id,
                "status": "missing",
                "content": "",
                "next_offset": offset,
                "done": True,
                "error": "Task not found",
            }

        log_path = Path(record.log_path)
        if not log_path.exists():
            return {
                "task_id": task_id,
                "status": record.status,
                "content": "",
                "next_offset": offset,
                "done": record.status in {"completed", "failed", "cancelled"},
            }

        with log_path.open("rb") as handle:
            handle.seek(offset)
            data = handle.read(limit)
            next_offset = handle.tell()
        return {
            "task_id": task_id,
            "status": record.status,
            "content": data.decode("utf-8", errors="ignore"),
            "next_offset": next_offset,
            "done": record.status in {"completed", "failed", "cancelled"},
        }

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        record = self.get_record(task_id)
        if record is None:
            return {"task_id": task_id, "cancelled": False, "error": "Task not found"}

        if record.status in {"completed", "failed", "cancelled"}:
            return {
                "task_id": task_id,
                "cancelled": False,
                "status": record.status,
                "error": "Task already finished",
            }

        process = self._processes.get(task_id)
        if process is not None:
            record.status = "cancelled"
            record.finished_at = time.time()
            self._terminate_process(process)
            try:
                await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=2)
            except asyncio.TimeoutError:
                self._kill_process(process)
                await asyncio.to_thread(process.wait)
            record.exit_code = process.returncode
            self._save_record(record)
            return {"task_id": task_id, "cancelled": True, "status": record.status}

        job = self._async_jobs.get(task_id)
        if job is not None:
            record.status = "cancelled"
            record.finished_at = time.time()
            self._save_record(record)
            job.cancel()
            try:
                await job
            except asyncio.CancelledError:
                pass
            return {"task_id": task_id, "cancelled": True, "status": record.status}

        return {
            "task_id": task_id,
            "cancelled": False,
            "status": record.status,
            "error": "Task is not cancellable",
        }


_MANAGERS: Dict[str, BackgroundTaskManager] = {}


def get_background_task_manager(workdir: Optional[str | Path] = None) -> BackgroundTaskManager:
    cwd = Path(workdir or Path.cwd()).resolve()
    key = str(cwd)
    manager = _MANAGERS.get(key)
    if manager is None:
        manager = BackgroundTaskManager(cwd)
        _MANAGERS[key] = manager
    return manager
