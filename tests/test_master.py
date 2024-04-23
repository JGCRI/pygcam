from __future__ import print_function
from six import iteritems
from itertools import chain
import ipyparallel as ipp
from ipyparallel.client.client import ExecuteReply


# Remotely-called function; imports requirement internally.
def dummyTask(key):
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
    def getInstance(cls, profile=None, cluster_id=None, sleepSeconds=SLEEP_SECONDS):
        """
        Return singleton instance of this class
        """
        if not cls.instance:
            cls.instance = cls(profile=profile, cluster_id=cluster_id)

        cls.instance.setSleepSeconds(sleepSeconds)
        return cls.instance

    def __init__(self, profile=None, cluster_id=None):
        self.client = ipp.Client(profile=profile, cluster_id=cluster_id)
        self.statusDict = {}
        self.sleepSeconds = SLEEP_SECONDS
        self.keyField = 'key'

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
        try:
            dv = self.client[:]
        except ipp.NoEnginesRegistered as e:
            print('queueTotals: %s' % e)
            return

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
        try:
            results = ar.get()
        except Exception as e:
            print('getResults: %s' % e)
            return

        client.purge_results(jobs=tasks) # so we don't see them again

        # filter out results from execute commands (e.g. imports)
        results = [r[0] for r in results if r and not isinstance(r, ExecuteReply)]
        return results

    def runTasks(self, count, clearStatus=False):
        if clearStatus:
            self.clearStatus()

        view = self.client.load_balanced_view()
        arList = []

        for key in range(1, count + 1):
            ar = view.apply_async(dummyTask, key)
            arList.append(ar)
            self.setStatus(key, 'queued')

        return arList

    def checkRunning(self):
        running = self.runningTasks()
        if running:
            try:
                # _logger.debug("Found %d running tasks", len(running))
                ar = self.client.get_result(running, block=False)
                statusDict = self.statusDict
                # print('statusDict:', statusDict)
                for dataDict in ar.data:
                    for key, status in iteritems(dataDict):
                        currStatus = statusDict.get(key)
                        if currStatus != status:
                            self.setStatus(key, status)
            except Exception as e:
                print("checkRunning: %s" % e)
                return

    def processResult(self, result):
        key = result[self.keyField]
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
                if not results:
                    print("Completed tasks have no results: engine died?")
                    continue    # is this recoverable?

                for result in results:
                    self.processResult(result)


if __name__ == '__main__':

    #
    # Test with custom worker func and subclass
    #
    def runTrial(argDict):
        from time import sleep
        from random import random
        from ipyparallel.datapub import publish_data

        def randomSleep(minSleep, maxSleep):
            delay = minSleep + random() * (maxSleep - minSleep)
            sleep(delay)
            argDict['slept'] = '%.2f' % delay

        runId = argDict['runId']

        publish_data({runId: 'running'})
        randomSleep(10, 15)
        publish_data({runId: 'finishing'})
        sleep(2)
        return argDict


    class NewMaster(BaseMaster):
        def __init__(self, profile=None, cluster_id=None):
            super(NewMaster, self).__init__(profile=profile, cluster_id=cluster_id)
            self.keyField = 'runId'

        def runTrials(self, tuples, clearStatus=False):
            if clearStatus:
                self.clearStatus()

            view = self.client.load_balanced_view(retries=1)    # in case engine fails, retry job once only
            asyncResults = []
            argDict = {}

            try:
                for runId, trialNum in tuples:
                    argDict['trialNum'] = trialNum
                    argDict['runId'] = runId

                    # Easier to deal with a list of AsyncResults than a single
                    # instance that contains info about all "future" results.
                    result = view.map_async(runTrial, [argDict])
                    asyncResults.append(result)
                    self.setStatus(runId, 'queued')

            except Exception as e:
                print("Exception running 'runTrial': %s", e)

        def processResult(self, result):
            key = result[self.keyField]
            self.setStatus(key, 'completed')
            print("Completed", result)


    testBase = False
    profile  = None
    cluster_id = None

    if testBase:
        m = BaseMaster.getInstance(sleepSeconds=5)
        m.runTasks(6, clearStatus=True)
    else:
        m = NewMaster.getInstance(sleepSeconds=3, profile=profile, cluster_id=cluster_id)
        tuples = [(runId, trialNum) for runId, trialNum in enumerate(range(1000, 1020))]
        m.runTrials(tuples, clearStatus=True)

    m.processResults()
    print('Status:')
    d = m.statusDict
    for runId in sorted(d.keys()):
        print('  runId %s: %s' %(runId, d[runId]))
