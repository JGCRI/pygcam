Installation
==================

There are two options for installing and using pygcam and :doc:`gcamtool`.

  - :ref:`Option 1 <option1>` -- **This option is recommended for most users.** It creates
    a new virtual environment for pygcam based
    on an "environment" file that identifies specific versions of all python modules required
    by ``pygcam``. This approach is fairly fool-proof, but it does require that you
    "activate" the pygcam environment before using it.

  - :ref:`Option 2 <option2>` installs ``pygcam`` as a standard Python package, making
    it available for use in your own Python programming efforts, while also providing
    access to gcamtool. This sometimes creates conflicts between pygcam's requirements
    and those of other packages you may have installed, and may require familiarity
    with Python to create a working environment.

.. note::

   You must run the ``init`` sub-command to initialize your configuration file
   (``~/.pygcam.cfg``) prior to using :doc:`gcamtool`. See the :doc:`initialize`
   for further details. (You can, however, run ``gt``
   or any sub-command with the ``-h`` or ``--help`` option to get help, even before
   initializing.)

-----------------------------------

.. _option1:

Option 1: Install pygcam in a virtual environment
---------------------------------------------------

This is the recommended option for most users, as it is the most reliable. Use
:ref:`Option 2 <option2>` if you need to integrate ``pygcam`` with other Python
packages and you are more familiar with managing package dependencies.

1. Download and install `Anaconda 5 <https://www.anaconda.com/download>`_
   (the **Python 2.7** version!) for your platform.

   * Note that you must either allow the Anaconda installer to set the required
     ``PATH`` elements, or you must set them yourself.

   * On macOS and Linux (assuming you installed Anaconda in your home directory) these
     are ``$HOME/anaconda2`` and ``$HOME/anaconda2/bin``. You can add these to your
     ``PATH`` using this command:
     ``PATH="$HOME/anaconda2:$HOME/anaconda2/bin"``

   * On Windows, it's easiest to let Anaconda set the ``PATH`` for you. If you do it
     manually, add both the ``Anaconda2`` directory (typically in C:/Users/*your name*/Anaconda2)
     and the ``Anaconda2\Scripts`` directory below that, to your ``PATH``.

2. Download the environment file for your platform from
   https://anaconda.org/plevin/pygcam/files by selecting
   ``pygcam_windows.yml``, ``pygcam_macos.yml``, or ``pygcam_linux.yml``.

3. Run the following command, replacing the ``/path/to/file.yml`` with the
   path to the file you downloaded in step 2:

  .. code-block:: bash

     # Replace "/path/to/file.yml" with path to the file you downloaded
     conda env create -f /path/to/file.yml

4. To activate the new environment (which is necessary before you use ``pygcam``),
   run the following command:

   * On MacOS and Linux::

       source activate pygcam

   * On Windows using :ref:`cygwin <cygwin-label>`, note that there are bugs in the
     ``activate`` and ``deactivate`` scripts.
     You can download corrected versions of these from https://bitbucket.org/snippets/plevin/.
     Download both the ``activate.cygwin`` and ``deactivate.cygwin`` scripts and save them
     to your ``Anaconda2/Scripts`` directory. The you can run::

       source activate.cygwin pygcam

   * If you are using a standard Windows command prompt, type this command::

       activate pygcam

See the `conda <https://conda.io/docs/user-guide/tasks/manage-environments.html>`_
documentation for further details.

.. _option2:

Option 2: Install pygcam into your current python environment
--------------------------------------------------------------

1. Run the command:

  .. code-block:: sh

     pip install pygcam

Note that you may run into package conflicts this way. Options 1 or 2 are more reliable.


Quick Links
^^^^^^^^^^^^^

  - `Download Anaconda 5 <https://www.anaconda.com/download>`_
  - :ref:`Install pygcam <pygcam_install_label>`


.. _install-anaconda:

Install Anaconda
^^^^^^^^^^^^^^^^^

  .. note::

     Be sure to install Anaconda for **Python 2.7!** Pygcam does not yet run in Python 3.

The most convenient way to install and manage a scientific Python environment
is to use the free `Anaconda 5 <https://www.anaconda.com/download>`_ distribution.
Anaconda includes most of the scientific and statistical modules used by ``pygcam``.
You can, however, use any installation of Python **2.7** if you prefer. Without
Anaconda you may have to install more packages. Note that all development and
testing of pygcam uses Anaconda. Follow the installation instructions for you
platform.

  - `Download Anaconda 5 <https://www.anaconda.com/download>`_

If you mistakenly install Python 3, I recommend uninstalling it to avoid confusion. Creating
a Python 2.7 virtual environment from a Python 3 installation requires more work than simply
downloading the correct Python 2.7 version of Anaconda.

  .. _pygcam_install_label:


Working with pygcam source code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you have a valid Python 2.7 environment installed, you can install
``pygcam``. There are two primary ways to install pygcam (or any open source
package) depending on how you want to use the software.

As described above, you can install pygcam as a standard Python package,
using the command:

.. code-block:: bash

   pip install pygcam

If you are interested in working with the source code (e.g., writing plugins or
adding functionality), you should clone the code repository to create a local
copy. You can then install ``pygcam`` in "developer" mode using the ``setup.py``
script found in the top-level ``pygcam`` directory. This creates links from the
installed package to the source code repository so changes to the source code are
"seen" immediately without requiring reinstallation of ``pygcam``.

.. code-block:: bash

   # First, uninstall pygcam if you installed it previously. This ensures that
   # the "develop" version isn't shadowed by previously installed files.
   pip uninstall pygcam

   # Change directory to where you want the pygcam folder to be "cloned"
   git clone https://github.com/JGCRI/pygcam.git
   cd pygcam

   # Install pygcam in developer mode
   python setup.py develop

The ``setup.py`` script uses a Python module called ``setuptools``. On Mac OS X and
Linux, ``setup.py`` installs ``setuptools`` automatically. Unfortunately, automating
this failed on Windows, so if the commands above fail, you will have to install
``setuptools``. To install ``setuptools`` manually, run this command in a terminal:

.. code-block:: bash

   conda install setuptools

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

Download the appropriate ``setup.exe`` version (usually the 64-bit version). Run it and, for
most people, just accept the defaults. You might choose a nearby server for faster downloads.

I recommend installing just these for now (easy to add more later):

  - under *Editors*

    - **nano** (a very simple text editor useful for modifying config files and such)

    Editors popular with programmers include ``emacs`` and ``vim``, though these have a steeper
    learning curve than ``nano``.

  - Under *shells*:

    - **bash-completion** (saves typing; see bash documentation online)

Anaconda activate and deactivate scripts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
There are bugs in the standard Anaconda2 ``activate`` and ``deactivate`` scripts that
cause these to function incorrectly under cygwin. You can download corrected versions of
these from https://bitbucket.org/snippets/plevin/.

Download both the ``activate.cygwin`` and ``deactivate.cygwin`` scripts and save them
to your ``Anaconda2/Scripts`` directory. The you can run::

       source activate.cygwin pygcam

to start using the ``pygcam`` environment, and::

       source deactivate.cygwin

to stop using it. (Necessary only if you need to switch to another Anaconda environment.)

----------------------------------------

Installing GCAM and Java
---------------------------

Regardless of how you've installed ``pygcam``, you will also need to install GCAM itself,
which in turn requires java.

This is a short guide to these topics since they are outside the scope of ``pygcam``.
See the `GCAM <https://github.com/JGCRI/gcam-core/releases>`_ website for the most
up-to-date information.

Quick Links
^^^^^^^^^^^^^

  - `Download install-gcam.py <https://raw.githubusercontent.com/JGCRI/pygcam/master/install-gcam.py>`_
  - `Download GCAM <https://github.com/JGCRI/gcam-core/releases>`_
  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_


Install GCAM
^^^^^^^^^^^^^^

.. note::
   The instructions below refer to installing GCAM v4.3, released in 2016. A new version of GCAM
   will be released sometime in early November, 2017, at which point these instructions may become obsolete.

You probably already have GCAM or you wouldn't be reading this. You can follow the
installation instructions on the official `GCAM <https://github.com/JGCRI/gcam-core/releases>`_
website, but some users have found these instructions confusing.

Alternatively, you can use my
`install-gcam.py <https://raw.githubusercontent.com/JGCRI/pygcam/master/install-gcam.py>`_ script
which handles downloading, unpacking, and setting up GCAM (which, on the Mac, this requires setting
a symbolic link to the java libraries, which the script handles for you.) Right click on the link
above and save the file to your system. To see the available command-line options, run the command:

.. code-block:: sh

   python install-gcam.py -h

::

 usage: install-gcam.py [-h] [-d DOWNLOADDIR] [-i INSTALLDIR] [-k] [-n] [-r]

 Install GCAM v4.3 on Windows, macOS, or Linux

 optional arguments:
   -h, --help            show this help message and exit
   -d DOWNLOADDIR, --downloadDir DOWNLOADDIR
                         The directory into which to download the required tar
                         files. Default is $HOME/.gcam-installation-tmp
   -i INSTALLDIR, --installDir INSTALLDIR
                         The directory into which to install GCAM 4.3. Default
                         is $HOME/gcam-v4.3-install-dir
   -k, --keepTarFiles    Keep the downloaded tar files rather than deleting
                         them.
   -n, --noRun           Print commands that would be executed, but don't run
                         them.
   -r, --reuseTarFiles   Use the already-downloaded tar files rather then
                         retrieving them again. Implies -k/--keepTarFiles.

The script requires Python 2.x (as does pygcam). If you have Python installed, you
can use it to run this script, which uses only standard modules. If you need to
install Python, follow the instructions for :ref:`installing Anaconda <install-anaconda>`,
then you can download and run the install script. The installation script runs on all three
GCAM platforms (MacOS, Windows, and Linux.)

Install Java
^^^^^^^^^^^^^^^^^^
You need a Java installation to run GCAM. If the link below doesn't work, find
the latest version of Java available from `Oracle <http://www.oracle.com>`_.

  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_

