#!/usr/bin/env python
#
# Copyright (C) 2016, the ximpol team.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU GengReral Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""Unit test for the irf.arf module.
"""

import unittest
import os
import numpy

from ximpol.irf.arf import *
from ximpol.core.spline import xInterpolatedUnivariateSplineLinear


class TestXipeArf(unittest.TestCase):

    """Unit test for the XIPE effective area.
    """

    def test_xipe_arf(self):
        """Test the XIPE effective area.

        This is loading the effective area from the .arf FITS file, then
        loading the data points from the text files the response function
        is created from, and finally testing that the actual values from the
        two methods are close enough over the entire energy range.
        """
        from ximpol import XIMPOL_IRF
        from ximpol.detector.xipe import OPT_AEFF_FILE_PATH,\
            GPD_QEFF_FILE_PATH, IRF_NAME
        arf_file_path = os.path.join(XIMPOL_IRF, 'fits', '%s.arf' % IRF_NAME)
        _x, _y = numpy.loadtxt(OPT_AEFF_FILE_PATH, unpack=True)
        opt_aeff = xInterpolatedUnivariateSplineLinear(_x, _y)
        _x, _y = numpy.loadtxt(GPD_QEFF_FILE_PATH, unpack=True)
        gpd_eff = xInterpolatedUnivariateSplineLinear(_x, _y)
        aeff = xEffectiveArea(arf_file_path)
        _x = numpy.linspace(aeff.xmin, aeff.xmax, 100)
        _delta = abs((aeff(_x) - opt_aeff(_x)*gpd_eff(_x))/aeff(_x))
        self.assertTrue(_delta.max() < 5e-3, 'max. diff. %.9f' % _delta.max())


if __name__ == '__main__':
    unittest.main()
