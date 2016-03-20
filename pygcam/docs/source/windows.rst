Using pygcam under Microsoft Windows
====================================

Installation
------------

To use pygcam under Windows, the easiest approach is to install the
`Anaconda <https://www.continuum.io/downloads>`_ distribution, though you can
use any installation of Python 2.7. Without Anaconda, you'll just have to install
more packages. (The setup script takes care of this.)

  - `Download <https://www.continuum.io/downloads>`_ and install Anaconda with Python 2.7

  - Install pygcam:

    ``python setup.exe install``


Initialize the configuration file
----------------------------------

Run ``gtwin.py -h``, which will print a usage message and create
an initial configuration file, unless one is already present. The
file is ``.pygcam.cfg`` found in your home directory.

**Document why these should be changed**

  .. code-block:: cfg

    [DEFAULT]

    # Change this if desired
    GCAM.LogLevel = INFO

    # For our convenience
    User.RepoRoot = %(Home)s/bitbucket
    User.OtaqRoot = %(User.RepoRoot)s/otaq2016
    User.QueryDir = %(User.OtaqRoot)s/queries

    # For query command
    GCAM.QueryPath = %(User.QueryDir)s:%(User.QueryDir)s/Main_Queries_Customized.xml
    GCAM.RegionMapFile = %(User.OtaqRoot)s/etc/Regions.txt

    # For runProject command
    # For runProj
    GCAM.RunWorkspaceRoot = %(Home)s/ws
    GCAM.XmlSrc   = %(GCAM.RunWorkspaceRoot)s/xmlsrc
    GCAM.LocalXml = %(GCAM.RunWorkspaceRoot)s/local-xml


Install GCAM
------------

A convenient way to manage GCAM is to create a folder called GCAM in your home
directory. Copy the latest GCAM distribution (zip file) into this new directory,
and unzip it.

The file explorer unhelpfully creates two folders with the same name. That is,
if you unzip ``GCAM_4.2_r6539_User_Package_Windows.zip``, you end up
with a folder named ``GCAM_4.2_r6539_User_Package_Windows``, and within it, another
folder named ``GCAM_4.2_r6539_User_Package_Windows``. In the file explorer, change
the name of the outer folder to something else ('x' will do), and move the inner
folder up one level. Delete the empty outer folder ('x', or whatever you called it.)

Install Java
^^^^^^^^^^^^

You need a Java installation to run GCAM.
`Download <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_
it from Oracle for free.


Running python scripts
----------------------
Modify the ``PATH`` environment variable to include the location of the
``pygcam/bin`` folder, which holds the scripts.

To do this: Start menu -> right click on Computer -> Properties -> Advanced,
then edit the PATH by inserting the full path to your pygcam/bin folder,
with a semi-colon (;) separating path entries.

Optional: Running scripts without typing the ``.py`` extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  1. Modify the ``PATHEXT`` variable to include Python scripts, e.g.:

     ``PATHEXT=.COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.PY``

  2. In a command window, type the following commands. The first associates
     ``.py`` files with a file type ``Python.File``. The second specifies
     the command to run to execute files of the type ``Python.File``.

    .. code-block:: cfg

      assoc .py=Python.File
      ftype Python.File=c:\Users\{insert your user name}\Anaconda2\python.exe "%1" %*

*Note: The path after ``Python.File=`` should be the path to your python executable.*


Install Cygwin
-----------------------------

The pygcam scripts are run from the command-line, and the command-line tools in Windows are primitive.
I highly recommend installing the (free, open-source) `Cygwin <https://www.cygwin.com/>`_ package,
which is a set of libraries and programs that provides a Linux-like experience under Windows.

Running the pygcam scripts under the ``bash`` shell (or your favorite alternative) is more convenient
and it will start you up the learning curve to use the GCAM Monte Carlo framework, which runs only on
a Linux cluster. If you are a DOS power-user, use ``cmd.com`` or whatever you prefer.

Cygwin provides an installer GUI that lets you select which packages to install. There is a huge set
of packages, and you almost certainly won’t want all of it.

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

Don’t install python since we’re using Anaconda. Installing another python just confuses things.

Optionally, if you plan to work with the code in the ``git`` repository, download ``git``:

  - under *Devel*

    - **git** (select “git: Distributed version control system” and all the required libraries will be installed, too.)

Implementation notes
----------------------

In Unix-like systems, "symbolic links" (symlinks) are frequently used to provide shortcuts
or aliases to files and directories. The pygcam scripts use symlinks to create GCAM workspaces
without having to lots of large, read-only files. Rather, it creates workspaces with writable
directories where GCAM will create files at run-time, and it uses symlinks to the read-only
files (e.g., the GCAM executable) and folders (e.g., the ``input`` directory holding GCAM's
XML input files.

Windows (Vista and onward) also have symlinks, but these come with several caveats:

  - To remove a symlink to a file, use the ``del`` command
  - To remove a symlink to a folder, use ``rmdir`` (or ``rd`` for short).

    **Important note: using "del" on a symlink to a folder will offer to delete not just symlink,
    but also the files in the folder pointed to by the symlink.** (A nasty violation of the
    `principle of least astonishment <https://en.wikipedia.org/wiki/Principle_of_least_astonishment>`_.)

  - Either type of symlink can be removed using the file Explorer as well.

  - Symlinks work across devices and network, and through other symlinks, however, if you
    are working across multiple drives, be sure that you specify the drive letter (e.g., ``C:``)
    in the link target.

  - **NOTE** Symlinks can be created only on the NT File System (NTFS), not on FAT or FAT32, or
    network-mounted drives in other formats (e.g., Mac OS). This can be an issue if, for example,
    you want to keep your GCAM workspaces on an external drive. Pygcam will fail when trying to
    create symbolic links in those workspaces.

To work with the pygcam source code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To use pygcam and use it in development as well, use the following steps.
These are written assuming you have installed the Cygwin tools describe above.

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

  - Configure Anaconda to know where the source code version of pygcam lives.
    Create a file called
    ``/Users/{username}/AppData/Roaming/Python/Python27/site-packages/pygcam.pth``
    and add a line as shown, replacing {path to your repo} with, well, the path
    to your repository created earlier.

    .. code-block:: bash

       {path to your repo}/pygcam

    with the value replaced with the directory you created and into which
    you "cloned" pygcam.
