from pygcam.mcs.Database import getDatabase
from pygcam.mcs.util import createTrialString

db = getDatabase(checkInit=False)

simId = 1
df = db.getRunInfo(simId, 'baseline', includeSucceededRuns=False, asDataFrame=True)
print df

missing = db.getMissingTrials(simId, 'baseline')
s = createTrialString(missing)
print "Missing trials:", s

from pygcam.mcs.master import listTrialsToRedo

listTrialsToRedo(db, simId, ['baseline', 'corn'], ['missing', 'killed'])
