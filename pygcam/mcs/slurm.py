# Simple interface to some SLURM commands
#
# Copyright (c) 2017 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

import pandas as pd
import re
import six
import subprocess
import types

from pygcam.mcs.error import PygcamMcsException
from pygcam.log import getLogger

_logger = getLogger(__name__)

class Slurm(object):
    def __init__(self, *args, **kwargs):
        """
        Create a Slurm instance for interacting with SLURM commands.

        :param defaults: (dict) default values for common parameters so
            they don't have to be passed to all the individual commands.
        """
        import getpass

        self.username = kwargs.get('username') or getpass.getuser()

    def squeue(self, formatStr='%all', sep='|', otherArgs=''):
        """
        Run the squeue command and return a DataFrame with the results.

        :param formatStr: (str) format string indicating which data columns
           to list. Default is to list all columns, separated by '|'.
        :param sep: (str) separator to use between data columns
        :param otherArgs (str) other args to pass to squeue
        :return: status of shell command
        """
        command = "squeue -u %s -o '%s' %s" % (self.username, formatStr, otherArgs)
        _logger.debug(command)

        # Run command and read all results
        output = subprocess.check_output(command, shell=True).decode("utf-8")

        df = pd.read_table(six.StringIO(output), sep=sep, header=0, engine='c')
        df.fillna('', inplace=True)

        # Parse the overloaded nodelist column into separate columns
        colName = 'NODELIST(REASON)'
        if colName in df.columns:
            values = df[colName]
            pat1 = re.compile('([^\(]*)')       # anything up to a '('
            pat2 = re.compile('(\(.+\))') # anything between '(' and ')'

            def search(pat, s):
                matchObj = re.search(pat, s)
                return matchObj.group(1) if matchObj else ''

            df['NODELIST'] = [search(pat1, s) for s in values]
            df['REASON']   = [search(pat2, s) for s in values]

        return df

    def jobsInState(self, state, jobName=None):     # TBD: test this again
        """
        Return a list of jobIds for jobs in the given state.

        :param state: (str) standard SLURM state string (PENDING, RUNNING, etc.)
        :return: (list of int) the ids of the jobs owned by the user in the given
            state.
        """
        import platform
        if platform.system() != 'Linux':
            return []

        df = self.squeue(formatStr='%i|%j', otherArgs='-t ' + state.upper())
        jobs = df.loc[df.NAME == jobName, 'JOBID'] if jobName else df.JOBID
        return jobs

    def scancel(self, jobs):
        """
        Terminate the jobs identified by the given jobIds.

        :param jobs: (str or iterable of str) a jobId or sequence of jobIds
        :return: none
        """
        if isinstance(jobs, (list, tuple, set, types.GeneratorType)):
            jobStr = ' '.join(jobs)
        else:
            jobStr = str(jobs)

        command = "scancel " + jobStr
        _logger.debug(command)

        exitStatus = subprocess.call(command, shell=True)
        if exitStatus != 0:
            raise PygcamMcsException("Command failed: %s; exit status %s\n" % (command, exitStatus))

    def sbatch(self, script, queue):
        """
        Submit the given script to the given queue.

        :return: (int) jobId or -1 if shell command failed
        """
        command = "sbatch %s" % (script)

        # Run the sbatch command, parse the jobId if command succeeds
        jobStr = subprocess.check_output(command, shell=True).decode('utf-8')
        result = re.search('\d+', jobStr)
        jobId = int(result.group(0)) if result else -1
        return jobId


if __name__ == "__main__":
    output = '''JOBID|PARTITION|NAME|STATE|TIME|NODES|NODELIST(REASON)|TIMELIMIT|USER
3515574|shared|14100-5|RUNNING|1-23:35:42|1|node122|7-00:00:00|nand374
3515573|shared|14100-4|RUNNING|1-23:36:26|1|node122|7-00:00:00|nand374
3515572|shared|14100-3|RUNNING|1-23:37:09|1|node122|7-00:00:00|nand374
3515568|shared|14100-2|RUNNING|1-23:42:01|1|node122|7-00:00:00|nand374
3515438|shared|t14_4_1|PENDING|2-01:08:35|1||7-00:00:00|nand374
3515439|shared|t14_4_2|PENDING|2-01:08:35|1||7-00:00:00|nand374
3515440|shared|t14_4_3|RUNNING|2-01:08:35|1|node141|7-00:00:00|nand374
3515441|shared|t14_4_4|RUNNING|2-01:08:35|1|node141|7-00:00:00|nand374
3515442|shared|t14_4_5|RUNNING|2-01:08:35|1|node141|7-00:00:00|nand374
3515341|shared|t14_4_5|RUNNING|2-03:07:55|1|node141|7-00:00:00|nand374
3515339|shared|t14_4_4|RUNNING|2-03:11:47|1|node141|7-00:00:00|nand374
3515336|shared|t14_4_3|RUNNING|2-03:14:31|1|node141|7-00:00:00|nand374
3515334|shared|t14_4_2|RUNNING|2-03:15:30|1|node141|7-00:00:00|nand374
3515333|shared|t14_4_1|RUNNING|2-03:15:50|1|node141|7-00:00:00|nand374
'''
    pd.set_option('display.width', 1000)
    # df = pd.read_table(six.StringIO(output), sep='|', header=0, engine='c')

    slurm = Slurm(username='plev920')
    df = slurm.squeue(formatStr="%i|%P|%j|%u|%T|%M|%D|%R|%l")
    print(df)

    jobs = slurm.jobsInState('pending')
    print("Pending: %s" % jobs)

    jobs = slurm.jobsInState('running')
    print("Running: %s" % jobs)

