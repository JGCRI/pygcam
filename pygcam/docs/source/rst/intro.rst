Introduction
============

The `pygcam` package offers Python-based software tools to help GCAM users work more efficiently with the
model. The tools are intended to meet the needs of different types of users, from basic users who just
want to run the model, to "power" users interested in writing custom scripts, to software developers
wanting to write new tools like graphical user interfaces for working with GCAM.

The main components include:

  * **Software libraries** that simplify development of higher-level software tools (graphical interfaces, scripts)
    that interface with GCAM. The library will provide an Application Programming Interface (API) to the GCAM input
    and output data, and to running GCAM, querying results, and performing common processing tasks such as computing
    differences between policy and baseline scenarios and plotting results.

  ..

  * **Command-line tools** built upon the library described above to package commonly required functionality into a convenient
    form for direct use and to support development of higher-level, custom scripts.

  ..

  * **A Monte Carlo Simulation framework** using GCAM on high-performance computers, allowing users to explore
    uncertainty in model outputs resulting from uncertainty in model inputs, and to characterize the contribution of
    individual parameters to variance in output metrics.

  .. * (Eventually) **Graphical User Interfaces** that simplify use of the libraries and tools as well
     as providing unique capabilities such as graphical exploration and comparison of sets of model
     results.

  * **User documentation** for all of the above.

  ..

  * **Cross-platform capability** on Windows, Mac OS X, and Linux.

  ..

  * **Installer scripts** to simplify installation of tools on users’ computers.
