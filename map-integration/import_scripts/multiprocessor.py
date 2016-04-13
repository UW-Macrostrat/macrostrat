import multiprocessing
from shapely.geometry import mapping, shape
from shapely.ops import cascaded_union


class Processor(multiprocessing.Process):

  def __init__(self, task_queue, result_queue):
    multiprocessing.Process.__init__(self)
    self.task_queue = task_queue
    self.result_queue = result_queue

  def run(self):
    proc_name = self.name
    while True:
      next_task = self.task_queue.get()
      if next_task is None:
          print 'Tasks complete on this thread'
          self.task_queue.task_done()
          break
      answer = next_task()
      self.task_queue.task_done()
      self.result_queue.put(answer)
    return


class Task(object):
  # Assign check and year when initialized
  def __init__(self, geoms):
    self.geoms = geoms

  # Acts as the controller for a given year
  def __call__(self):
      return cascaded_union(self.geoms)
