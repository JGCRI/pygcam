Using pygcam on PIC
====================

This page describes how to use ``pygcam`` on the PNNL Institutional Computing (PIC)
system. Others may find some of it useful for tips on how to setup ``pygcam`` for
multiple users on similar high-performance computing systems.

Several files have been installed in ``/pic/projects/GCAM`` and configured
to simplify use of ``pygcam`` on PIC.

Anaconda
----------
There is a shared installation of the Anaconda2 Python package in
``/pic/projects/GCAM/anaconda2``. To use it, make sure that
``/pic/projects/GCAM/anaconda2/bin`` is in your ``PATH`` before
any other Python installations. (This is done for you in the
``pygcam.sh`` script described below.)

Module conflicts
^^^^^^^^^^^^^^^^
To avoid confusion, it would be best to unload any other Python or Anaconda modules
you may have loaded:

 .. code-block:: sh

    module unload python/2.7.3
    module unload python/2.7.8
    module unload python/3.4.2
    module unload python/anaconda2
    module unload python/anaconda3

It may be possible, at times, to run ``pygcam`` with the standard anaconda2
module, but ``pygcam`` is under active development, and the version installed in
``/pic/projects/GCAM`` will be kept current with respect to python module requirements.


pygcam.sh
---------------
The shell script ``/pic/projects/GCAM/pygcam-support/pygcam.sh`` can be
read into your current shell to configure several environment variables
as needed for ``pygcam``. Add the line:

 .. code-block:: sh

    source /pic/projects/GCAM/pygcam-support/pygcam.sh

to your ``.bashrc``. If you are using a shell with different
syntax, please post the converted file to this directory with
an appropriate suffix so others can use it.

The script ``pygcam.sh`` contains the following:

 .. code-block:: sh

    PIC_GCAM=/pic/projects/GCAM
    PYGCAM_SUPPORT=$PIC_GCAM/pygcam-support

    export PYGCAM_SITE_CONFIG=$PYGCAM_SUPPORT/site.cfg

    # $PYGCAM_SUPPORT/bin provides access to the XML Starlet (xml) program
    export PATH="$PIC_GCAM/anaconda2/bin:$PYGCAM_SUPPORT/bin:$PATH"

site.cfg
----------
PIC-specific configuration settings for ``pygcam`` are available in the
file ``/pic/projects/GCAM/pygcam-support/site.cfg``. To cause ``pygcam``
to read this, set the environment variable ``PYGCAM_SUPPORT`` to the
path to this file. Note that this is done for you in ``pygcam.sh``.
If you are using a custom version of GCAM, you will need to modify these
settings.

 .. code-block:: cfg

    #
    # This file sets site defaults for pygcam configuration parameters.
    # It is read after system.cfg and before reading the user's ~/.pygcam.cfg
    # file.
    #
    [DEFAULT]
    PIC.GCAMDir             = /pic/projects/GCAM
    PIC.Lib                 = %(PIC.GCAMDir)s/GCAM-libraries/lib

    # Set GCAM.VersionNumber to 4.3 to use that version.
    GCAM.VersionNumber      = 4.4
    GCAM.RefWorkspace       = %(PIC.GCAMDir)s/pygcam-support/gcam-core-gcam-v%(GCAM.VersionNumber)s

    GCAM.MI.Dir             = %(GCAM.RefWorkspace)s/input/gcam-data-system/_common/ModelInterface/src
    GCAM.MI.ClassPath       = %(PIC.Lib)s/%(GCAM.VersionNumber)s/*:%(PIC.Lib)s/jars/*:%(GCAM.MI.JarFile)s:XMLDBDriver.jar

    GCAM.DefaultQueue       = short,slurm
    PIC.AccountFlag         = -A GCAM
    GCAM.OtherBatchArgs     = %(PIC.AccountFlag)s

    # If you run GCAM with the in-memory database, you might want to reserve
    # more memory. Setting "-n 3" reserves 3/24 cores, which allocates 1/8th of
    # the 64 GB (i.e., 8 GB) of memory. In this mode you might also want to use
    # the "shared" queue, which you can do by adding the following two lines to
    # your ~/.pygcam.cfg file:
    # GCAM.DefaultQueue = shared
    # GCAM.OtherBatchArgs = %(PIC.AccountFlag) -n 3


Running scenario groups
------------------------

The most convenient way to run a scenario group on PIC (or any cluster)
is to use the ``-D`` or ``--distribute`` option to the run sub-commmand. For
example, to run the default scenario group for project "Foo", you can run:

      ::

         gt +P Foo run -D

This will queue the baseline scenario and then queue the policy scenarios
with a dependency on successful completion of the baseline scenario job.

      ::

         gt +P Foo run -D -S baseline,policy-1

If scenarios are explicitly named, only those scenarios are run, as usual.
If none of the named scenarios is a baseline, the jobs are all queued
immediately.

You can run all scenarios in all scenario groups using this same mechanism
by specifying the ``-a`` or ``--allGroups`` flag:

    ::

       gt +P Foo run -D -a

This command is equivalent to iterates over all groups and running ``gt run -D``
on each group. All the baselines will start immediately, and all the policy
scenarios will be queued with a dependency on successful completion of the
corresponding baseline.
