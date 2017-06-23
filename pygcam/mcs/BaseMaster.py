from __future__ import print_function
import ipyparallel as ipp
from six import iteritems
from itertools import chain


# Remotely-called function; imports requirement internally.
def runTrial(key):
    from os import getpid
    from time import sleep
    from ipyparallel.datapub import publish_data

    publish_data({key: 'running'})
    sleep(2 * key)
    publish_data({key: 'finishing'})
    sleep(2)
    return {'key': key, 'pid': getpid()}


# Default time to wait in main hub polling/result processing loop
SLEEP_SECONDS = 3


class BaseMaster(object):
    instance = None

    @classmethod
    def getInstance(cls, sleepSeconds=SLEEP_SECONDS):
        """
        Return singleton instance of this class
        """
        if not cls.instance:
            cls.instance = cls()

        cls.instance.setSleepSeconds(sleepSeconds)
        return cls.instance

    def __init__(self):
        self.client = ipp.Client()
        self.statusDict = {}
        self.sleepSeconds = SLEEP_SECONDS

    def setSleepSeconds(self, secs):
        self.sleepSeconds = secs

    def clearStatus(self):
        self.statusDict = {}

    def setStatus(self, key, status):
        self.statusDict[key] = status

    def queueTotals(self):
        """
        Return totals for queue status across all engines
        """
        dv = self.client[:]
        qstatus = dv.queue_status()

        totals = dict(queue=0, completed=0, tasks=0)

        for id, stats in iteritems(qstatus):
            if id == u'unassigned':
                totals[id] = stats
            else:
                for key, count in iteritems(stats):
                    totals[key] += count

        return totals

    def runningTasks(self):
        qstatus = self.client.queue_status(verbose=True)
        ids = [rec['tasks'] for key, rec in iteritems(qstatus) if isinstance(key, (int, long))]
        return list(chain.from_iterable(ids))

    def completedTasks(self):
        recs = self.client.db_query({'completed': {'$ne': None}}, keys=['msg_id'])
        ids = [rec['msg_id'] for rec in recs] if recs else None
        return ids

    def getResults(self, tasks):
        if not tasks:
            return None
        client = self.client
        ar = client.get_result(tasks, owner=True, block=False)
        results = ar.get()
        client.purge_results(jobs=tasks) # so we don't see them again
        return results

    def runTrials(self, count, clearStatus=False):
        if clearStatus:
            self.clearStatus()

        view = self.client.load_balanced_view()
        arlist = []
        for key in range(1, count + 1):
            ar = view.apply_async(runTrial, key)
            arlist.append(ar)
            self.setStatus(key, 'queued')
        return arlist

    def checkRunning(self):
        running = self.runningTasks()
        if running:
            # _logger.debug("Found %d running tasks", len(running))
            ar = self.client.get_result(running, block=False)
            statusDict = self.statusDict
            print('statusDict:', statusDict)
            for dataDict in ar.data:
                for key, status in iteritems(dataDict):
                    currStatus = statusDict.get(key)
                    if currStatus != status:
                        self.setStatus(key, status)

    def processResult(self, result):
        key = result['key']
        self.setStatus(key, 'completed')
        print("Completed", key)

    def processResults(self):
        from time import sleep

        while True:
            sleep(self.sleepSeconds)
            self.checkRunning()

            tot = self.queueTotals()
            print(tot)
            if not (tot['queue'] or tot['tasks'] or tot['unassigned']) and \
                    not self.completedTasks():
                return

            completed = self.completedTasks()
            if completed:
                results = self.getResults(completed)
                for result in results:
                    self.processResult(result)

if __name__ == '__main__':
    m = BaseMaster.getInstance(sleepSeconds=5)
    m.runTrials(6, clearStatus=True)
    m.processResults()
    print("Done.")
