import uuid
import random

from tasks import Task
from requester import Requester


class DataStore(object):
    def __init__(self):
        self._tasks = {}
        self.requester = Requester(self)

    def has_task(self, tid):
        if tid in self._tasks:
            return True
        return False

    def get_requester(self):
        return self.requester

    def get_tasks_tree(self):
        return self._tasks

    def get_all_tasks(self):
        """ Returns a list of strings: tasks ids """
        return list(self._tasks.keys())

    def get_task(self, tid):
        if self.has_task(tid):
            return self._tasks[tid]
        else:
            return None

    def new_task(self):
        tid = str(uuid.uuid4())
        task = Task(tid, True)
        self._tasks[tid] = task
        return task

    def push_task(self, task):
        def adding(task):
            self._tasks[task.get_id()] = task

        if self.has_task(task.get_id()):
            return False
        else:
            adding(task)
            return True

    def request_task_deletion(self, tid):
        self.requester.delete_task(tid)
        # if self.has_task(tid):
        #    del self._tasks[tid]
        #    return True
        # else:
        #    return False

    def populate(self, ex_tasks):
        # ex_tasks[] = [title, start_date, due_date, done?]
        for i in range(0, len(ex_tasks)):
            new_task = self.new_task()
            new_task.set_title(ex_tasks[i][0])
            new_task.set_start_date(ex_tasks[i][1])
            new_task.set_due_date(ex_tasks[i][2])
            if ex_tasks[i][3]:
                new_task.set_status(Task.STA_DONE)
            new_task.set_color(ex_tasks[i][4])

    def get_random_task(self):
        if self._tasks:
            return random.choice(list(self._tasks.keys()))
        return None
