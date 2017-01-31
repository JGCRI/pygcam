Installation
==================

There are two modes of installing and using pygcam and :doc:`gcamtool`.

  - :ref:`Option 1 <option1>` (available only to Mac and Windows users) installs an
    all-in-one :doc:`gcamtool` directory created by
    `pyinstaller <https://pythonhosted.org/PyInstaller>`_ that provides a
    stand-alone version of gcamtool and all supporting files.
    This is the simplest approach to gaining access to the :doc:`gcamtool` command.

  - :ref:`Option 2 <option2>` (the only option for Linux users) installs ``pygcam`` as a standard Python
    package, making it available for use in your own Python programming efforts, while also
    providing access to gcamtool.

.. note::
   Both options require that you install java and (of course) GCAM, as described below.

Required software
-------------------

Quick Links
^^^^^^^^^^^^^

  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_
  - `Download GCAM <https://github.com/JGCRI/gcam-core/releases>`_

Java
^^^^^^^^^^^^^^^^
You need a Java installation to run GCAM. If the link below doesn't work, find
the latest version of Java available from `Oracle <http://www.oracle.com>`_.

  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_

GCAM
^^^^^^^^
You probably already have GCAM or you wouldn't be reading this. But for completeness:

  - `Download GCAM <https://github.com/JGCRI/gcam-core/releases>`_

Create a file structure for GCAM and pygcam
"""""""""""""""""""""""""""""""""""""""""""""""
A convenient way to manage GCAM is to create a folder called GCAM in your home
directory (or anywhere you prefer). Copy the latest GCAM distribution into this
directory, and unpack the files. (Follow the instructions at the link above.)

Within this folder you might create a symbolic link called ``current`` which
points to the current version of GCAM. This allows you to switch versions simply
by changing the symbolic link. All ``pygcam`` configuration and project information
will remain valid unless the internal file structure of the GCAM distribution
changes, which may require an update to ``pygcam``.

Note that ``pygcam`` sets the following default values for the following
:doc:`config` variables; these may need to be updated for your installation.

    .. code-block:: cfg

       GCAM.Root         = %(Home)s/GCAM
       GCAM.SandboxRoot  = %(GCAM.Root)s/ws
       GCAM.Current      = %(GCAM.Root)s/current
       GCAM.RefWorkspace = %(GCAM.Current)s


The first time ``gt`` is run, it will create a default
configuration file with all options present but commented out.
Running ``gt -h``, will print a usage message and create
the initial configuration file (unless one is already present). The
file is ``.pygcam.cfg`` found in your home directory.


---------------------------------------------------------------------------

.. _xmlstarlet-label:

XML starlet
^^^^^^^^^^^^

.. note::

   Prior to version 1.0b2, ``pygcam`` required the xmlstarlet command-line program,
   however, subsequent versions have eliminated this dependency by implementing
   the required functionality using the Python lxml library. The following instructions
   pertain only to 1.0b1 and earlier, and will be removed after beta testing is complete.

The `XML Starlet <http://xmlstar.sourceforge.net/download.php>`_ program is a
command-line tool that can search and edit XML files, among other tricks.
It is available for all three GCAM platforms, and should already be included on all
modern Linux systems. It is available from the download page in
binary (executable) form for Windows, but must be compiled on Mac OS X. Binary versions
are available on https://bitbucket.org/plevin/pygcam/downloads, but owing to differences
in library versions and locations, these are not guaranteed to work on you system. (A
better solution is in the works...)

Mac users might first try the version provided
`here <https://bitbucket.org/plevin/pygcam/downloads/xmlstarlet-osx.zip>`_. Simply
download the file, double-click on it in finder to unzip it, and move the resulting
``xml`` file to somewhere in your path, which might include ``/usr/local/bin`` or ``$HOME/bin``.

For Mac users,
a `homebrew recipe <http://macappstore.org/xmlstarlet/>`_ is available to build it on
your machine if you have homebrew and developer tools (Xcode) installed. Alternatively,
here are `instructions <http://michael-joseph.me/en/linux-en/how-to-install-xmlstarlet-on-mac-osx/>`_
on downloading and building xmlstarlet.

Once installed, be sure the ``xml`` (starlet) program is available on your ``PATH``
or set the ``GCAM.XmlStarlet`` config variable to the program, either in your own
``$HOME/.pygcam.cfg`` file or the site configuration file, if one is used.
The default setting requires that the program be found on your ``PATH``:

  .. code-block:: cfg

     GCAM.XmlStarlet = xml

Note that the official site provides a binary version only for Windows. My own copies of binaries
are provided here:

  - `Download binaries of XML Starlet from the pygcam site <https://bitbucket.org/plevin/pygcam/downloads>`_.

Unfortunately, given the vagaries of dynamic libraries, I cannot guarantee that these
binaries will work on your machine. I provide them in the hope that they will help someone!
A future version of pygcam may eliminate this dependency.

---------------------------------------------------------------------------

.. _option1:

Option 1: Download the all-in-one zip file
------------------------------------------
Starting with ``pygcam`` version 1.0b2, Mac and Windows users have the option of
downloading a zip file with an all-in-one :doc:`gcamtool` directory created by
`pyinstaller <https://pythonhosted.org/PyInstaller>`_ that provides a
stand-alone version of gcamtool and all supporting files. To use this:

  - Download the latest version of the gt zip file from the
    `pygcam downloads <https://bitbucket.org/plevin/pygcam/downloads>`_ page.
  - Unzip the downloaded zip file anywhere on your system.
  - Set the PATH environment variable to top-level folder created from the zip file.

See the specific instructions for Macintosh and Windows users, below.


Macintosh users
^^^^^^^^^^^^^^^^
1. Download `gt-1.0b8-mac.zip <https://bitbucket.org/plevin/pygcam/downloads/gt-1.0b8-mac.zip>`_.

2. Double-click on the downloaded zip file to unzip it, creating the directory ``gt-1.0b8-mac`` (or similar,
   depending on the version). Move that directory anywhere you like. You might move it to your home directory,
   or to where you store GCAM-related files.

3. To set the PATH variable to the correct location, edit your shell startup file (e.g., .bashrc
   for bash users) to add the full pathname of the unzipped directory to the PATH. For example, if
   you move the unzipped folder to your home directory (which can be referenced as ``$HOME``) you would
   add this line to ``$HOME/.bashrc``:

   .. code-block:: sh

      export PATH="$HOME/gt-1.0b2-mac:$PATH"

   For additional help setting the PATH variable for other shells, see this
   `Apple webpage <https://developer.apple.com/library/content/documentation/OpenSource/Conceptual/ShellScripting/shell_scripts/shell_scripts.html>`_.


Windows users
^^^^^^^^^^^^^^
1. Download `gt-1.0b2-win.zip <https://bitbucket.org/plevin/pygcam/downloads/gt-1.0b8-win.zip>`_.

2. Right click on the zip file and select "Extract all...". If you accept the default path presented
   in the dialog box, Windows will create a redundant directory level, i.e., ``gt-1.0b8/gt-1.0b8``.
   If you do this, move the inner directory to where you would like to keep the gcamtool files and
   then delete the outer directory. Alternatively, you can edit the path presented in the dialog box
   to remove the final ``gt-1.0b8``, so that the unzipped folder will have only one level called ``gt-1.0b8``.

3. To add the location of the gcamtool folder to your PATH, see this
   `page <http://www.computerhope.com/issues/ch000549.htm>`_.

Additional information is available below :ref:`for Windows users <windows-label>`.

-------------------------

.. _option2:

Option 2: Install python and the pygcam package
------------------------------------------------

If you intend to use ``pygcam`` as a library for Python programming, or if you
intend to modify or debug (thanks!) the code, you must install a Python environment
and then install ``pygcam`` as a standard python package. These steps are describe
below.

Note that this is the only installation option available to Linux users.


Quick Links
^^^^^^^^^^^^^

  - `Download Anaconda 2 <https://www.continuum.io/downloads>`_
  - :ref:`Install pygcam <pygcam_install_label>`


Install Anaconda
^^^^^^^^^^^^^^^^^

  .. note::

     Be sure to install Anaconda for **Python 2.7!** Pygcam does not yet run in Python 3.

The most convenient way to install and manage a scientific Python environment
is to use the free `Anaconda <https://www.continuum.io/downloads>`_ distribution.
Anaconda includes most of the scientific and statistical modules used by ``pygcam``.
You can, however, use any installation of Python **2.7** if you prefer. Without
Anaconda you may have to install more packages. Note that all development and
testing of pygcam uses Anaconda. Follow the installation instructions for you
platform.

  - `Download Anaconda 2 <https://www.continuum.io/downloads>`_

If you mistakenly install Python 3, you might want to delete it (unless you plan to
use it for other purposes) to avoid confusion. Creating a Python 2.7 virtual environment
requires more work than simply downloading the correct Python 2 version of Anaconda.


  .. _pygcam_install_label:

Install pygcam
^^^^^^^^^^^^^^^^^
Once you have a valid Python 2.7 environment installed, you can install
``pygcam``. There are two primary ways to install pygcam (or any open source
package) depending on how you want to use the software.

Most users will want to simply install pygcam as a standard Python package,
using the command:

  .. code-block:: bash

       $ pip install pygcam

If you are interested in working with the source code (e.g., writing plugins or
adding functionality), you should clone the code repository to create a local
copy. You can then install ``pygcam`` using the ``setup.py`` script found in
the top-level ``pygcam`` directory:

  .. code-block:: bash

     # First, change directory to where you want the pygcam folder to be "cloned"

     $ git clone git@bitbucket.org:plevin/pygcam.git
     $ cd pygcam

There are two options for installing from the source code. The first method installs
``pygcam`` to the normal location using the current version of the code in the cloned
repository:

  .. code-block:: bash

     $ python setup.py install

However, if you make changes to the code, or pull updates into your cloned repo, you
will have to re-install pygcam.

The ``setup.py`` script can also install ``pygcam`` by creating references back to the
source code and therefore you need not re-install every time you make changes to the code.
To do this, run the command:

  .. code-block:: bash

     $ python setup.py develop

The ``setup.py`` script uses a Python module called ``setuptools``. On Mac OS X and
Linux, ``setup.py`` installs ``setuptools`` automatically. Unfortunately, automating
this failed on Windows, so if the commands above fail, you will have to install
``setuptools``. To install ``setuptools`` manually, run this command in a terminal:

  .. code-block:: bash

     $ conda install setuptools


-----------------------------------

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

.. note::
   Don’t install Cygwin's version of python if you’re using Anaconda.
   Installing multiple versions of Python just confuses things.

Download the appropriate setup.exe version (probably 64-bit). Run it and, for most people, you'll
just accept all the defaults. You might choose a nearby server for faster downloads.

I recommend installing just these for now (easy to add more later):

  - under *Editors*

    - **nano** (a very simple text editor useful for modifying config files and such)

    Editors popular with programmers include ``emacs`` and ``vim``, though these have a steeper
    learning curve than ``nano``.

  - Under *shells*:

    - **bash** (The GNU Bourne Again Shell -- this is the terminal program)
    - **bash-completion** (saves typing; see bash documentation online)
