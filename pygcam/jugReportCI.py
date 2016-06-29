#!/usr/bin/env python
import jug
jug.init(jugfile='jugWorker.py', jugdir='jugdir')
import jugWorker

results = jugWorker.getResults(simId=1, trialStr="1-20", baseline="RefMar15", scenarioStr="corn")

print "Success:"
for r in filter(lambda result: result.status == 0, results):
    print(r)

print "\nFailure:"
for r in filter(lambda result: result.status, results):
    print(r)
    #print("%s %s %s" % (r.context, r.step, r.policy or ''))
