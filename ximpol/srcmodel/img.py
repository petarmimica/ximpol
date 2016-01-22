#!/urs/bin/env python
#
# Copyright (C) 2015, the ximpol team.
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


from astropy.io import fits
import aplpy
import numpy

from ximpol.utils.logging_ import logger
from ximpol.utils.matplotlib_ import pyplot as plt
from ximpol.utils.matplotlib_ import context_no_grids


class xFitsImage(aplpy.FITSFigure):

    """Class describing a FITS image.

    Warning
    -------
    There are several things I don't quite understand here, first of all
    why we seem to need to transpose the data. (Also, we migh have a
    residual offset by 1 pixel that we should try and sort out.)
    """

    def __init__(self, file_path):
        """Constructor.
        """
        logger.info('Reading FITS image from %s...' % file_path)
        self.hdu_list = fits.open(file_path)
        self.hdu_list.info()
        self.data = self.hdu_list['PRIMARY'].data.transpose()
        self.cdf = numpy.cumsum(self.data.ravel())
        self.cdf /= self.cdf[-1]
        aplpy.FITSFigure.__init__(self, self.hdu_list['PRIMARY'])
        plt.close()

    def rvs_coordinates(self, size=1, randomize=True):
        """Generate random coordinates based on the image map.
        """
        u = numpy.random.rand(size)
        pixel = numpy.searchsorted(self.cdf, u)
        row, col = numpy.unravel_index(pixel, self.data.shape)
        ra, dec = self.pixel2world(row, col)
        if randomize:
            delta_ra = 0.5*self.hdu_list['PRIMARY'].header['CDELT1']
            delta_dec = 0.5*self.hdu_list['PRIMARY'].header['CDELT2']
            ra += numpy.random.uniform(-delta_ra, delta_ra, size)
            dec += numpy.random.uniform(-delta_dec, delta_dec, size)
        return ra, dec

    def __call__(self, row, column):
        """Return the value of the underlying map for a given pixel.
        """
        return self.data[i][j]

    def plot(self, show=True):
        """Plot the image.
        """
        self.add_grid()
        self.show_colorscale(cmap = 'afmhot')
        plt.show()




def main():
    """
    """
    import os
    from ximpol import XIMPOL_SRCMODEL
    file_path = os.path.join(XIMPOL_SRCMODEL, 'fits', 'crab_0p3_10p0_keV.fits')
    img = xFitsImage(file_path)
    ra, dec = img.rvs_coordinates(1000000)
    print(ra)
    print(dec)
    plt.hist2d(ra, dec, bins=500)
    plt.show()


if __name__ == '__main__':
    main()