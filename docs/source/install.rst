Installation
==================

Quick Links:

  - `Download Anaconda <https://www.continuum.io/downloads>`_
  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_
  - `Download XML Starlet <http://xmlstar.sourceforge.net/download.php>`_.
  - `Download GCAM <http://www.globalchange.umd.edu/models/gcam/download>`_
  - :ref:`Install pygcam <pygcam_install_label>`

Follow the steps below to install these. Additional information is available
below :ref:`for Windows users <windows-label>`.

  .. note::

     ``pygcam`` requires a Python 2.7 environment. A Python 3 version will
     be availabe at some point, but isn't presently.


Support software
--------------------------

Anaconda
^^^^^^^^^^^^^^^^^
The most convenient way to install and manage a scientific Python environment
is to use the free `Anaconda <https://www.continuum.io/downloads>`_ distribution.
Anaconda includes most of the scientific and statistical modules used by ``pygcam``.
You can, however, use any installation of Python **2.7** if you prefer. Without
Anaconda you may have to install more packages. Note that all development and
testing of pygcam uses Anaconda.

  - `Download Anaconda <https://www.continuum.io/downloads>`_

Java
^^^^^^^^^^^^^^^^
You need a Java installation to run GCAM. If the link below doesn't work, find
the latest version of Java available from `Oracle <http://www.oracle.com>`_.

  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_

.. _xmlstarlet-label:

XML starlet
^^^^^^^^^^^^
The :doc:`setup` system (and the underlying :doc:`pygcam.xmlEditor` module) rely
on the `XML Starlet <http://xmlstar.sourceforge.net/download.php>`_ program, a
command-line tool that can search and edit XML files, among other tricks.
It is available for all three GCAM platforms, and should already
be included on all modern Linux systems. It is available from the download page in
binary (executable) form for Windows, but must be compiled on Mac OS X. Contact the
author if you need a copy for the Mac.

Once installed, be sure the ``xml`` (starlet) program is available on your ``PATH``
or set the ``GCAM.XmlStarlet`` config variable to the program, either in your own
``$HOME/.pygcam.cfg`` file or the site configuration file, if one is use.
The default setting is:

  .. code-block:: cfg

     GCAM.XmlStarlet = xml


  - `Download XML Starlet <http://xmlstar.sourceforge.net/download.php>`_.

GCAM and pygcam
------------------------

GCAM
^^^^^^^^^^^^^^^^^
You probably already have GCAM or you wouldn't be reading this. But for completeness:

  - `Download GCAM <http://www.globalchange.umd.edu/models/gcam/download>`_

Create a file structure for GCAM and pygcam
"""""""""""""""""""""""""""""""""""""""""""""""
A convenient way to manage GCAM is to create a folder called GCAM in your home
directory (or anywhere you prefer). Copy the latest GCAM distribution (zip file)
into this directory, and unzip the file.

Within this folder you might create a symbolic link called ``current`` which
points to the current version of GCAM. This allows you to switch versions simply
by changing the symbolic link. All ``pygcam`` configuration and project information
will remain valid unless the internal file structure of the GCAM distribution
changes, which may require an update to ``pygcam``.

Note that on Windows, the file explorer unhelpfully creates two folders with the
same name. That is, if you unzip ``GCAM_4.2_r6539_User_Package_Windows.zip``, you
end up with a folder named ``GCAM_4.2_r6539_User_Package_Windows``, and within it,
another folder named ``GCAM_4.2_r6539_User_Package_Windows``. In the file explorer,
change the name of the outer folder to something else ('x' will do), and move the inner
folder up one level. Delete the empty outer folder ('x', or whatever you called it.)

Note also that ``pygcam`` sets the following default values for the following
configuration variables; these may need to be updated for your installation.

    .. code-block:: cfg

       GCAM.Root         = %(Home)s/GCAM
       GCAM.SandboxRoot  = %(GCAM.Root)s/ws
       GCAM.Current      = %(GCAM.Root)s/current
       GCAM.RefWorkspace = %(GCAM.Current)s/Main_User_Workspace

  .. _pygcam_install_label:

Install pygcam
-------------------
Once you have a valid Python 2.7 environment installed, you can install
``pygcam`` using this command:

       ``pip install pygcam``

This will be appropriate for most users.

Working with the pygcam source code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you are interested in working with the source code (e.g., writing plugins or
adding functionality), you should clone the code repository to create a local
copy. You can then install ``pygcam`` using the ``setup.py`` script found in
the top-level ``pygcam`` directory:

  .. code-block:: bash

     python setup.py install

which will install ``pygcam`` to the normal location using the current version
of the code in the inner ``pygcam`` directory.

Note that the ``setup.py`` script provides an option that install ``pygcam``
by creating references to the source code and therefore you need not re-install
every time you make changes to the code. To do this, run the command:

  .. code-block:: bash

     python setup.py develop

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
    - **bash-completion** (saves typing; see bash documentation online)

.. note::
   Don’t install Cygwin's version of python if you’re using Anaconda.
   Installing multiple versions of Python just confuses things.
