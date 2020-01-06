import time
import schedule as schedule


class Scheduler(object):
    """
    A scheduler used to schedule a job defined in mail.scheduling.jobs
    """

    def __init__(self, interval: int):
        """interval: the length of time in seconds paused between runs"""
        self.interval = interval

    def add_job(self, job: object):
        """add a job to this scheduler"""
        schedule.every(self.interval).seconds.do(job)

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
