Installation
==================

.. note::
   If you are having trouble running ``pygcam`` and are running a version older than
   ``v1.0.1`` or are having difficulties installing ``pygcam``, you can resolve many problems
   by running these commands after activating your ``pygcam`` environment::

     pip uninstall pygcam              # not necessary if not yet installed
     pip install pyscaffold==2.5.8
     pip install salib==1.1.2
     pip install pygcam

   You can check the version you have installed by running the command ``gt --version``.

   If you have not yet created an Anaconda environment for ``pygcam``, download the
   environment file for your system as described in :ref:`Option 1 <option1>`,
   below.

There are two options for installing and using pygcam and :doc:`gcamtool`.

  - :ref:`Option 1 <option1>` -- **This option is recommended for most users.** It creates
    a new virtual environment for pygcam based on an "environment" file that identifies
    specific versions of all python modules required by ``pygcam``. This approach is
    fairly fool-proof, but it does require that you "activate" the pygcam environment
    before using it.

  - :ref:`Option 2 <option2>` installs ``pygcam`` as a standard Python package, making
    it available for use in your own Python programming efforts, while also providing
    access to gcamtool. This sometimes creates conflicts between pygcam's requirements
    and those of other packages you may have installed, and may require familiarity
    with Python to create a working environment.

.. note::

   You must run the ``init`` sub-command to initialize your configuration file
   (``~/.pygcam.cfg``) prior to using most :doc:`gcamtool` commands. See the
   :doc:`initialize` for further details. (You can, however, run ``gt --version``
   or any command with the ``-h`` or ``--help`` option to get
   help before initializing.)

-----------------------------------

.. _option1:

Option 1: Install pygcam in a virtual environment
---------------------------------------------------

This is the recommended option for most users, as it is the most reliable. Use
:ref:`Option 2 <option2>` if you need to integrate ``pygcam`` with other Python
packages with specific requirements and you are more familiar with managing package
dependencies.

1. Download and install `Anaconda <https://www.anaconda.com/download>`_ for your platform.

The most convenient way to install and manage a scientific Python environment
is to use the free `Anaconda <https://www.anaconda.com/download>`_ distribution.
Anaconda includes most of the scientific and statistical modules used by ``pygcam``.
You can, however, use any installation of Python if you prefer. Without
Anaconda you may have to install more packages. Note that all development and
testing of pygcam uses Anaconda. Follow the installation instructions for your
platform.

    .. note::

       Starting with pygcam v1.3.1, you can use either the Python 2.x or 3.x versions
       of Anaconda 5. As of this writing, the current versions are Anaconda 5.3 and Python
       versions 2.7 or 3.7. Older versions of pygcam require **Python 2.7**.

   * On Windows, you can use the Anaconda Prompt from the Start menu to open a
     command prompt that refers to the Anaconda installation. Alternatively, you can
     allow the Anaconda installer to set the required ``PATH`` elements (or set them yourself)
     to use Anaconda from a standard Windows command prompt. If you do this
     manually, add the directories ``Anaconda2`` and ``Anaconda2/Scripts`` (for Python 2),
     or ``Anaconda3`` and ``Anaconda3/Scripts`` (for Python 3) to your ``PATH``. The location
     and thus the full pathnames of these directories will depend on where you install Anaconda.

   * On macOS and Linux (assuming you installed Anaconda in your home directory) make sure
     ``$HOME/anaconda2`` and ``$HOME/anaconda2/bin`` (for Python 2) or
     ``$HOME/anaconda3`` and ``$HOME/anaconda3/bin`` (for Python 3) are in your
     ``PATH``. You can add these to your ``PATH`` using by adding this command to your
     shell's startup file:

     .. code-block:: bash

        # Adjust as needed if Anaconda is installed somewhere other than $HOME

        # For Anaconda2 / Python 2:
        PATH="$HOME/anaconda2:$HOME/anaconda2/bin"

        # For Anaconda3 / Python 3:
        PATH="$HOME/anaconda3:$HOME/anaconda3/bin"

2. Download the environment file for your platform by selecting one of the following.

   * For **Python 2.7**, go to https://anaconda.org/plevin/pygcam2/files and select from:

       * py2_pygcam_windows.yml
       * py2_pygcam_macos.yml
       * py2_pygcam_linux.yml

   * For **Python 3.7**, go to https://anaconda.org/plevin/pygcam3/files and select from:

       * py3_pygcam_macos.yml
       * py3_pygcam_windows.yml
       * py3_pygcam_linux.yml

3. Run the following command, replacing the ``/path/to/file.yml`` with the
   path to the file you downloaded in step 2:

  .. code-block:: bash

     # Replace "/path/to/file.yml" with path to the file you downloaded
     conda env create -f /path/to/file.yml

4. Activate the new environment:

   * On MacOS and Linux::

       source activate pygcam

   * On Windows using :ref:`cygwin <cygwin-label>`, note that there are bugs in the
     ``activate`` and ``deactivate`` scripts.
     You can download corrected versions of these from https://bitbucket.org/snippets/plevin/.
     Download both the ``activate.cygwin`` and ``deactivate.cygwin`` scripts and save them
     to your ``Anaconda2/Scripts`` directory. The you can run::

       source activate.cygwin pygcam

   * If you are using a standard Windows command prompt or an Anaconda prompt,
     type this command::

       activate pygcam

   .. note::

      You will need to activate the pygcam environment whenever you open a new
      terminal to work with :doc:`gcamtool`.

5. Finally, install the pygcam package into the newly created environment::

     pip install pygcam

.. seealso::

   See the `conda <https://conda.io/docs/user-guide/tasks/manage-environments.html>`_
   documentation for further details on managing environments.


.. _option2:

Option 2: Install pygcam into your current python environment
--------------------------------------------------------------

1. Run the command:

  .. code-block:: sh

     pip install pygcam

Note that you may run into package conflicts this way. Option 1 is more reliable.


Working with pygcam source code
--------------------------------

If you are interested in working with the source code (e.g., writing plugins or
adding functionality), you should clone the code repository (https://github.com/JGCRI/pygcam)
to create a local copy. You can then install ``pygcam`` in "developer" mode using the ``setup.py``
script found in the top-level ``pygcam`` directory. This creates links from the
installed package to the source code repository so changes to the source code are
available immediately without requiring reinstallation of ``pygcam``.

.. code-block:: bash

   # Uninstall pygcam if you installed it previously: this avoids
   # potential conflicts with previously installed files.
   pip uninstall pygcam

   # Change directory to where you want the pygcam folder to be "cloned"
   cd (wherever you want)

   # Clone the git repository
   git clone https://github.com/JGCRI/pygcam.git
   cd pygcam

   # Install pygcam in developer mode
   python setup.py develop

The ``setup.py`` script uses a Python module called ``setuptools``. On Mac OS X and
Linux, ``setup.py`` installs ``setuptools`` automatically. Unfortunately, this has
been less reliable on Windows, so if the commands above fail, you will have to install
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
without having to make copies of lots of large, read-only files. Rather, it creates workspaces with writable
directories where GCAM will create files at run-time, and it uses symlinks to the read-only
files (e.g., the GCAM executable) and folders (e.g., the ``input`` directory holding GCAM's
XML input files).

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
  - To remove a symlink to a file, use the ``del`` command.
  - To remove a symlink to a folder, use ``rmdir`` (or ``rd`` for short).

    **Using "del" on a symlink to a folder will offer to delete not just symlink,
    but also the files in the folder pointed to by the symlink.** (An unfortunate
    violation of the
    `principle of least astonishment <https://en.wikipedia.org/wiki/Principle_of_least_astonishment>`_.)

  - Either type of symlink can be removed using the file Explorer as well.

  - Symlinks work across devices and network, and through other symlinks. However, if you
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
which in turn requires Java.

This is a short guide to these topics since they are outside the scope of ``pygcam``.
See the `GCAM <https://github.com/JGCRI/gcam-core/releases>`_ website for the most
up-to-date information.

Quick Links
^^^^^^^^^^^^^

  - `Download install-gcam.py <https://raw.githubusercontent.com/JGCRI/pygcam/master/install-gcam.py>`_ (Helpful for GCAM 4.3).
  - `Download GCAM <https://github.com/JGCRI/gcam-core/releases>`_
  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_


Install GCAM
^^^^^^^^^^^^^^

GCAM v5.1.1
~~~~~~~~~~~~
GCAM v5.1.1 was also released in July, 2018. Download MacOS or Windows binary packages, or source packages
for Linux from the `GCAM v5.1.1 <https://github.com/JGCRI/gcam-core/releases/tag/gcam-v5.1.1>`_ release page.

GCAM v4.4.1
~~~~~~~~~~~
GCAM v4.4.1, which was released in July 2018 (a bug fix for v4.1, released in November 2017),
has single-file packages for macOS and Windows.
Download these from the `GCAM v4.4.1 <https://github.com/JGCRI/gcam-core/releases/tag/gcam-v4.4.1>`_ release page.

For users building GCAM from source, you will need the both the source code (either the ``.zip``
or ``.tar.gz`` version) as well as ``data-system.tar.gz``: after unpacking the source files, change
directory to the ``input/gcam-data-system`` directory before untarring the data system files.

GCAM v4.3
~~~~~~~~~~~
You can follow the installation instructions on the `GCAM <https://github.com/JGCRI/gcam-core/releases>`_
web page, but some users have found these instructions confusing.

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

The script requires Python 2.x. If you have Python installed, you
can use it to run this script, which uses only standard modules. If you need to
install Python, follow the instructions above for installing Anaconda,
then you can download and run the install script. The installation script runs on all three
GCAM platforms (MacOS, Windows, and Linux.)

Install Java
^^^^^^^^^^^^^^^^^^
You need a Java installation to run GCAM. If the link below doesn't work, find
the latest version of Java available from `Oracle <http://www.oracle.com>`_.

  - `Download Java <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`_

