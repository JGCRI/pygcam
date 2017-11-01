MCS Explorer
==============

The MCS Explorer is a new interactive tool for exploring Monte Carlo simulation results.
It is currently undergoing active development, but as it is already useful, it has been
included in the current pygcam release.

Features
--------
The MCS Explorer provides a web-based interface by running a local web application server
based on the `dash <https://plot.ly/products/dash/>`_ platform, which was released in mid-2017.
The application provides:

* Histogram showing frequency distributions for selected model out

* Tornado chart showing which parameters are top contributors to uncertainty
  in the selected model output

* Interactive parallel-coordinates plot showing combinations of parameter values,
  colored by the results they produce for the selected model output

* Scatterplots showing relationship between selected model inputs and outputs

An example is shown below.

  .. image:: ../images/explorer.jpg


Running the MCS Explorer
-------------------------
The MCS Explorer reads your ``.pygcam.cfg`` file to discover the projects you have defined,
and to locate the MCS database for each project. It initially selects your default
project, but you can select other defined projects from a pull-down menu.

Next, the MCS database is read to discover the simulations and scenarios you have run,
and the model results you have captured. These are are presented in pull-down menus.

You can run the MCS Explorer locally on your desktop computer, by downloading
the ``pygcammcs.sqlite`` database from the cluster where your ran the MCS, or by
running the Explorer remotely on a Linux cluster and "tunneling" via the ``ssh``
command to connect a desktop browser with the remote application.

Using a local database
^^^^^^^^^^^^^^^^^^^^^^^
To work locally, your database must be at the location indicated in your
``.pygcam.cfg`` file by the variable ``MCS.DbPath``. You can check the
current value of the variable with the command:

  .. code-block:: sh

     $ gt config dbpath

which will show a value like

  .. code-block:: sh

     [paper1]
               MCS.DbPath = /Users/rjp/mcs/paper1/db/pygcammcs.sqlite

After moving the database (or editing your config file to set a different value
for ``MCS.DbPath``, run the command:

  .. code-block:: sh

     $ gt explore

This will start the web application server on your desktop computer. Point your
browser at the URL http://127.0.0.1:8050 to load the MCS Explorer application.

Using a remote database
^^^^^^^^^^^^^^^^^^^^^^^^^
Use ``ssh`` to login to the remote machine, using the ``-L`` option
to indicate that port 8050 on your desktop computer should be forwarded
to port 8050 on ``localhost`` (interpreted from the remote system's
perspective, i.e., the remote system itself.)

  .. code-block:: sh

     $ ssh -L 8050:localhost:8050 username@remote.host.name

Of course, change ``username`` and ``remote.host.name`` to appropriate values.

Once logged into the remote system, run the MCS Explorer there, with the command:

  .. code-block:: sh

     $ gt explore

This will start the web application server on the remote system. Point a browser
on your desktop computer at the URL http://localhost:8050 to load the MCS Explorer
application.


Scatter plots
--------------
  .. image:: ../images/scatter.jpg


Correlation convergence
------------------------
  .. image:: ../images/convergence.jpg
