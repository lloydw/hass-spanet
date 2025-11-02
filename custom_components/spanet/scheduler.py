import time
import logging
import traceback

logger = logging.getLogger(__name__)

class Task:
    def __init__(self, interval: int, callback):
        self.interval = interval
        self.callback = callback
        self.next_tick = 0
        self.error_count = 0

    def trigger(self, delay=None):
        self.next_tick = (int(time.time()) + delay) if delay != None else 0


class Scheduler:

    def __init__(self):
        self.tasks = []

    def add_task(self, interval: int, callback):
        task = Task(interval, callback)
        self.tasks.append(task)
        return task

    async def tick(self):
        now = int(time.time())
        for task in self.tasks:
            if task.next_tick <= now:
                try:
                    await task.callback()
                    task.error_count = 0
                except Exception as e:
                    task.error_count = task.error_count + 1
                    logger.error(f"Error #{task.error_count} running task {task.callback.__name__}\n{traceback.format_exc()}\n")

                # If the error count is 1, we're going to try again next tick
                if task.error_count != 1:
                    task.next_tick = now + task.interval
