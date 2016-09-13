Installation
==================
To run ``pygcam``, you need a Python 2.7 environment, Java, and GCAM.
Follow the steps below to install these. Additional information is available
below :ref:`for Windows users <windows-label>`.

Install support software
--------------------------

Anaconda
^^^^^^^^^^^^^^^^^
A convenient way to install and manage a Python environment is to use
the free `Anaconda <https://www.continuum.io/downloads>`_ distribution.
You can use any installation of Python **2.7** if you prefer. Anaconda
includes most of the scientific and statistical modules used by ``pygcam``.
Without Anaconda you may have to install more packages.

  - `Download Anaconda <https://www.continuum.io/downloads>`_

Java
^^^^^^^^^^^^^^^^
You need a Java installation to run GCAM. If the link below doesn't work, find
the latest version of Java available from `Oracle <http://www.oracle.com>`_.

  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_

GCAM
^^^^^^^^^^^^^^^^^
You probably already have GCAM or you wouldn't be reading this. But for completeness:

  - `Download GCAM <http://www.globalchange.umd.edu/models/gcam/download>`_

Setting up a structure for ``pygcam``
""""""""""""""""""""""""""""""""""""""""
A convenient way to manage GCAM is to create a folder called GCAM in your home
directory (or anywhere you prefer). Copy the latest GCAM distribution (zip file)
into this directory, and unzip the file.

Within this folder you might create a symbolic link called ``current`` which
points to the current version of GCAM. This allows you to switch versions simply
by changing the symbolic link. All ``pygcam`` configuration and project information
will remain valid (unless, of course, the internal file structure of the GCAM
distribution changes.)

Note that on Windows, the file explorer unhelpfully creates two folders with the
same name. That is, if you unzip ``GCAM_4.2_r6539_User_Package_Windows.zip``, you
end up with a folder named ``GCAM_4.2_r6539_User_Package_Windows``, and within it,
another folder named ``GCAM_4.2_r6539_User_Package_Windows``. In the file explorer,
change the name of the outer folder to something else ('x' will do), and move the inner
folder up one level. Delete the empty outer folder ('x', or whatever you called it.)

Install ``pygcam``
-------------------
You can install ``pygcam`` directly from PyPi using the command:

       ``pip install pygcam``

If you are interested in working with the source code (e.g., writing plugins or
adding functionality), you might prefer to clone the code repository and use the
``setup.py`` script directly. (The ``setup.py`` script is found in the top-level
``pygcam`` directory.)

For added convenience when working with the code, install ``pygcam`` in "develop" mode,
which will create references to the source code and therefore will be updated whenever
you update the repository. To do this, run the command:

    ``python setup.py develop``

  - If you are not interested in maintaining links back to a source repository, you
    can run the standard installation procedure:

    ``python setup.py install``

The ``setup.py`` script uses a Python module called ``setuptools``. On Mac OS X and
Linux, ``setup.py`` installs ``setuptools`` automatically. Unfortunately, automating
this failed on Windows, so if the commands above fail, you will have to install
``setuptools``.

  - To install ``setuptools`` manually, run this command in a terminal:

    ``conda install setuptools``


Initialize the configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The first time ``gt`` is run, it will create a default
configuration file with all options present but commented out.
Running ``gt -h``, will print a usage message and create
the initial configuration file (unless one is already present). The
file is ``.pygcam.cfg`` found in your home directory.

Below are some key parameters you may wish to modify in your
``.pygcam.cfg`` file.

  .. code-block:: cfg

    [DEFAULT]

    # Set a default project to use if the "-P" flag is not specified to gt.
    GCAM.DefaultProject = XXX

    #
    # Define parameters specific to project "XXX"
    #
    [XXX]
    # Root directory in which to find user's project folders
    GCAM.ProjectRoot    = %(Home)s/GCAM/XXX-dir

    # The location of the default input file for the "run" sub-command
    GCAM.ProjectXmlFile = %(GCAM.ProjectRoot)s/etc/project.xml

    # These are used by the "query" sub-command
    GCAM.QueryPath      = %(QueryDir)s:%(QueryDir)s/Main_Queries_Customized.xml
    GCAM.RegionMapFile  = %(User.ProjectRoot)s/etc/Regions.txt

    # Change this if desired to increase or decrease diagnostic messages.
    # Possible values (from most to least verbose) are:
    # DEBUG, INFO, WARNING, ERROR, CRITICAL
    GCAM.LogLevel = DEBUG

    # Sets the directory under which the "gcam" sub-command should create GCAM
    # workspace directories before running GCAM
    GCAM.RunWorkspaceRoot = %(Home)s/ws

    # Tells gt where to look for plugins. Set to your project's plugin
    # directory if you have any plugins to load.
    # GCAM.PluginPath =



Default configuration variable dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The following figure shows variable dependencies according to the default
definitions. Variables lower in the figure depend on those above them. Thus,
if you change a variable with "descendants", you affect the definition of
everything below it in the figure. See the generated ``~/.pygcam.cfg`` for
further information.

  .. image:: images/ConfigVarStructure.jpg


Working with the pygcam source code
------------------------------------
To examine or modify the ``pygcam`` Python code, you need to download
the code using ``git``.

Unix-like platforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Unix-like platforms generally have ``git`` installed. Otherwise, install
a current version for your platform. Do the following:

  - Open a terminal window. (Mac users can find this in
    /Application/Utilities/Terminal.app)

  - For this example, we will create a folder called ``x`` in our home
    directory to hold the ``git`` repository. Use any name you prefer.
    Run these commands to download a copy of the Python files:

    .. code-block:: bash

       mkdir ~/bb
       cd ~/bb
       git clone git@bitbucket.org:plevin/pygcam.git

  - Configure Anaconda to know where the source code version of pygcam lives.
    **TO BE DONE**


Windows users
^^^^^^^^^^^^^^^^^^^^^^
These are instructions are written assuming you have installed the
Cygwin tools as described :ref:`below <cygwin-label>`. Use the
following steps:

  - Install git (or a GUI version like Tortoise.)

  - Make a new folder to hold your git repository. For the
    sake of an example, we'll make a new directory called
    ``bb`` (for bitbucket) in our home directory, but you
    can call this whatever you like.

    .. code-block:: bash

       mkdir ~/bb    # ~ is shorthand for your home directory

  - Open a ``cygwin terminal`` run these commands to download
    the source code:

    .. code-block:: bash

       cd ~/bb
       git clone git@bitbucket.org:plevin/pygcam.git

Tell python where ``pygcam`` is installed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To configure Anaconda to know where the source code version of pygcam is installed,
do the following.

  - Run the following command to have Python print out the location of the "user site"
    directory, i.e., where we will create a ".pth" file:

    .. code-block:: bash

       python -c 'import site; site._script()' --user-site

  - Create a file in  the "user site" directory called ``pygcam.pth``. The line should
    contain a single line with the full pathname to the location to the top-level
    folder of the ``pygcam`` source code. (The file can be called anything as long as
    it ends in ``.pth``.) You can do this with a text editor, or with the following
    commands, however be sure to replace *pygcam-source-path* with the path to
    the ``pygcam`` source, and *user-site-path* with the path displayed by the
    command above.

    .. code-block:: bash

       # For this example, we assume that the user site (printed by the
       # command above) is /Users/rjp/.local/lib/python2.7/site-packages,
       # and we have cloned pygcam into the folder /Users/rjp/bb/pygcam:

       echo /Users/rjp/bb/pygcam > /Users/rjp/.local/lib/python2.7/site-packages/pygcam.pth


.. _windows-label:

Using pygcam under Windows
---------------------------

The ``pygcam`` package was developed on Unix-like systems (Mac OS, Linux) and
subsequently ported to Microsoft Windows. This page provides Windows-specific
information.


Enable symbolic links
^^^^^^^^^^^^^^^^^^^^^

In Unix-like systems, "symbolic links" (symlinks) are frequently used to provide shortcuts
or aliases to files and directories. The pygcam scripts use symlinks to create GCAM workspaces
without having to lots of large, read-only files. Rather, it creates workspaces with writable
directories where GCAM will create files at run-time, and it uses symlinks to the read-only
files (e.g., the GCAM executable) and folders (e.g., the ``input`` directory holding GCAM's
XML input files.

Windows (Vista and onward) also have symlinks, but only administrators can create symlinks
**unless specific permission has been granted** to a user. To grant this permission, run the
Windows program ``gpedit.msc`` and select the option shown in the figure below. Edit the option
and add the desired user name to the list.

**Note, however, that the user cannot also be in the Administrator
group or the permission is "filtered" out.** (This seems to be a flaw in the design of the
permission system since one would expect rights to be the union of those for the groups one's
account is in.)

  .. image:: images/symlinkPermission.jpg

Also, note the following:
  - To remove a symlink to a file, use the ``del`` command
  - To remove a symlink to a folder, use ``rmdir`` (or ``rd`` for short).

    **Using "del" on a symlink to a folder will offer to delete not just symlink,
    but also the files in the folder pointed to by the symlink.** (An unfortunate
    violation of the
    `principle of least astonishment <https://en.wikipedia.org/wiki/Principle_of_least_astonishment>`_.)

  - Either type of symlink can be removed using the file Explorer as well.

  - Symlinks work across devices and network, and through other symlinks, however, if you
    are working across multiple drives, be sure that you specify the drive letter (e.g., ``C:``)
    in the link target or the path will be interpreted relative to the current drive.

  - **Symlinks can be created only on the NT File System (NTFS), not on FAT or FAT32, or
    network-mounted drives in other formats (e.g., Mac OS).** This can be an issue if, for example,
    you want to keep your GCAM workspaces on an external drive. Pygcam will fail when trying to
    create symbolic links in those workspaces.

.. _cygwin-label:

Using Cygwin
^^^^^^^^^^^^^^

Windows' native command-line tools are fairly primitive. For folks new to running
commmand-line programs, I recommend installing the
(free, open-source) `Cygwin <https://www.cygwin.com/>`_ package, which is a set of
libraries and programs that provides a Linux-like experience under Windows.

Using ``bash`` will start you up the learning curve to use the GCAM Monte Carlo framework,
which currently runs only on Linux systems.
The ``bash`` shell (or your favorite alternative) offers numerous nice features. Exploring
those is left as an exercise for the reader.

Cygwin provides an installer GUI that lets you select which packages to install. There is
a huge set of packages, and you almost certainly won’t want all of it.

Download the appropriate setup.exe version (probably 64-bit). Run it and, for most people, you'll
just accept all the defaults. You might choose a nearby server for faster downloads.

I recommend installing just these for now (easy to add more later):

  - under *Editors*

    - **nano** (a very simple text editor useful for modifying config files and such)

    Editors popular with programmers include ``emacs`` and ``vim``, though these have a steeper
    learning curve than ``nano``.

  - Under *shells*:

    - **bash** (The GNU Bourne Again Shell -- this is the terminal program)
    - **bash-completion** (saves a lot of typing)

.. note:: Don’t install python since we’re using Anaconda. Installing another version of Python just confuses things.

Optionally, if you plan to work with the code in the ``git`` repository, download ``git``:

  - under *Devel*

    - **git** (select “git: Distributed version control system” and all the required libraries will be installed, too.)

Alternatively, you might try the free `SourceTree <https://www.sourcetreeapp.com>`_ application
from Atlassian, which provides a nice user interface for ``git`` on Mac OS X and Windows.
