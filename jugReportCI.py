#!/usr/bin/env python
import jugCmd
jugCmd.init(jugfile='jugtest.py', jugdir='jugdir')
from jugtest import ciResults

results = jugCmd.task.value(ciResults)

print "Success:"
for r in filter(lambda result: result.status == 0, results):
    print("%s %s %.2f" % (r.context, r.policy, r.value))

print "\nFailure:"
for r in filter(lambda result: result.status, results):
    print("%s %s %s" % (r.context, r.step, r.policy or ''))
