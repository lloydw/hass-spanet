from datetime import datetime, timedelta

class Task:
    def __init__(self, interval: int, callback):
        self.interval = interval
        self.callback = callback
        self.next_tick = datetime.now()

    def trigger(self):
        self.next_tick = datetime.now()


class Scheduler:

    def __init__(self):
        self.tasks = []

    def add_task(self, interval: int, callback):
        task = Task(interval, callback)
        self.tasks.append(task)
        return task

    async def tick(self):
        for task in self.tasks:
            now = datetime.now()
            if task.next_tick <= now:
                await task.callback()
                task.next_tick = now + timedelta(seconds=task.interval)