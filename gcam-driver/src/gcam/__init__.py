#!/bin/env python
"""GCAM automation system package.

This package contains the modules that implement the GCAM automation system,
along with utility functions that are common to all GCAM functional areas.
Several GCAM functional areas also have subpackages that implement calculations
specific to those areas; for example, gcam.water for water downscaling or
gcam.land for land use downscaling.  The package also contains gcam_driver, a
stand-alone program for running the automation system.

"""


__all__ = ['util', 'water', 'modules']
