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
To run the MCS Explorer, run the command:

  .. code-block:: sh

     $ gt explore

This will start the local web application server. Point your browser at the URL
http://127.0.0.1:8050 to load the application.

The MCS Explorer reads your ``.pygcam.cfg`` file to discover the projects you have defined,
and to locate the MCS database for each project. It initially selects your default
project, but you can select other defined projects from a pull-down menu.

Next, the MCS database is read to discover the simulations and scenarios you have run,
and the model results you have captured. These are are presented in pull-down menus.



* Scatter plots

  .. image:: ../images/scatter.jpg

* Correlation convergence

  .. image:: ../images/convergence.jpg
