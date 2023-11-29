#!/usr/bin/env python
# Full license can be found in License.md
# Full author list can be found in .zenodo.json file
# DOI:10.5281/zenodo.1199703
#
# DISTRIBUTION STATEMENT A: Approved for public release. Distribution is
# unlimited.
# This work was supported by the Office of Naval Research.
# ----------------------------------------------------------------------------
"""Create a constellation with one testing instrument.

Attributes
----------
instruments : list
    List of pysat.Instrument objects

"""

import pysat

instruments = [pysat.Instrument('pysat', 'testing', clean_level='clean',
                                num_samples=10, update_files=True)]
