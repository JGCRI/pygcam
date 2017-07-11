# Simple interface to some SLURM commands
#
# Copyright (c) 2017 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

import pandas as pd
import re
import StringIO
import subprocess
import types

from .error import PygcamMcsException
from ..log import getLogger


_logger = getLogger(__name__)

# $ squeue -u nand374 -o '%all'
# ACCOUNT|GRES|MIN_CPUS|MIN_TMP_DISK|END_TIME|FEATURES|GROUP|SHARED|JOBID|NAME|COMMENT|TIMELIMIT|MIN_MEMORY|REQ_NODES|COMMAND|PRIORITY|QOS|REASON||ST|USER|RESERVATION|WCKEY|EXC_NODES|NICE|S:C:T|JOBID |EXEC_HOST |CPUS |NODES |DEPENDENCY |ARRAY_JOB_ID |GROUP |SOCKETS_PER_NODE |CORES_PER_SOCKET |THREADS_PER_CORE |ARRAY_TASK_ID |TIME_LEFT |TIME |NODELIST |CONTIGUOUS |PARTITION |PRIORITY |NODELIST(REASON) |START_TIME |STATE |USER |SUBMIT_TIME |LICENSES |CORE_SPECWORK_DIR
# ms3_slkmc|(null)|1|0|2017-07-09T17:55:00|(null)|users|no|3519210|targz|(null)|1:00:00|0||/pic/projects/interfaces/fenicr/gamma_only/In_Pure_Fe/targz.pic NEB_RUNS_6I NEB_RUNS_6I|0.00000021164306|normal|None||R|nand374|(null)|(null)||0|*:*:*|3519210 |node012 |24 |1 | |3519210 |100 |* |* |* |N/A |59:22 |0:38 |node012 |0 |short |909 |node012 |2017-07-09T16:55:00 |RUNNING |3271 |2017-07-09T16:54:22 |(null) |0/pic/projects/interfaces/fenicr/gamma_only/In_Pure_Fe

class Slurm(object):
    def __init__(self, *args, **kwargs):
        """
        Create a Slurm instance for interacting with SLURM commands.

        :param defaults: (dict) default values for common parameters so
            they don't have to be passed to all the individual commands.
        """
        import getpass

        self.username = kwargs.get('username') or getpass.getuser()

    def squeue(self, formatStr='%all', sep='|'):
        """
        Run the squeue command and return a DataFrame with the results.

        :param formatStr: (str) format string indicating which data columns
           to list. Default is to list all columns, separated by '|'.
        :param sep: (str) separator to use between data columns
        :return: status of shell command
        """
        command = "squeue -u %s -o '%s'" % (self.username, formatStr)
        _logger.debug(command)

        # Run command and read all results
        output = subprocess.check_output(command, shell=False)

        df = pd.read_table(StringIO.StringIO(output), sep=sep, header=0, engine='c')
        df.fillna('', inplace=True)
        return df

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

        exitStatus = subprocess.call(command, shell=False)
        if exitStatus != 0:
            raise PygcamMcsException("Command failed: %s; exit status %s\n" % (command, exitStatus))


    def sbatch(self, script, queue):
        """
        Submit the given script to the given queue.

        :return: (int) jobId or -1 if shell command failed
        """
        command = "sbatch %s" % (script)

        # Run the sbatch command, parse the jobId if command succeeds
        jobStr = subprocess.check_output(command, shell=False)
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
    df = pd.read_table(output, sep='|', header=0, engine='c')

    slurm = Slurm(username='plevin')
    df = slurm.squeue()
    print(df)
