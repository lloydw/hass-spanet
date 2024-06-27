import time

class Task:
    def __init__(self, interval: int, callback):
        self.interval = interval
        self.callback = callback
        self.next_tick = 0

    def trigger(self):
        self.next_tick = 0


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
                await task.callback()
                task.next_tick = now + task.interval