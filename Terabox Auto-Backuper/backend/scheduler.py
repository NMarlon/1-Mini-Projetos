"""Agendamento de sync periódico via APScheduler."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend import database


class SyncScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._job_id = "periodic_sync"
        self._callback = None

    def set_callback(self, callback):
        self._callback = callback

    async def start(self):
        interval = await database.get_setting("sync_interval_minutes")
        minutes = int(interval) if interval else 30
        auto_sync = await database.get_setting("auto_sync")
        if auto_sync == "true" and self._callback:
            self.scheduler.add_job(
                self._callback,
                trigger=IntervalTrigger(minutes=minutes),
                id=self._job_id,
                replace_existing=True,
            )
        self.scheduler.start()

    async def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def update_interval(self, minutes: int):
        if self.scheduler.get_job(self._job_id):
            self.scheduler.reschedule_job(
                self._job_id,
                trigger=IntervalTrigger(minutes=minutes),
            )

    async def enable(self, enabled: bool):
        if enabled and self._callback:
            interval = await database.get_setting("sync_interval_minutes")
            minutes = int(interval) if interval else 30
            self.scheduler.add_job(
                self._callback,
                trigger=IntervalTrigger(minutes=minutes),
                id=self._job_id,
                replace_existing=True,
            )
        else:
            job = self.scheduler.get_job(self._job_id)
            if job:
                job.remove()