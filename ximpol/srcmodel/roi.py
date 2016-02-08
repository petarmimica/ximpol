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


import numpy
from collections import OrderedDict

from ximpol.srcmodel.img import xFITSImage
from ximpol.srcmodel.spectrum import xCountSpectrum
from ximpol.evt.event import xMonteCarloEventList


class xModelComponentBase:

    """Base class for the source object.

    Note that the source identifier defaults to none and is typically assign
    after the fact when the source itself is added to a source model.

    Arguments
    ---------
    name : string
        The name of the source.

    identifier : int
        A unique identifier of the source within a ROI model.
    """

    def __init__(self, name, identifier=None, min_time=0., max_time=1000000.):
        """Constructor.
        """
        self.name = name
        self.identifier = identifier
        self.min_time = min_time
        self.max_time = max_time

    def rvs_sky_coordinates(self, size=1):
        """Generate random coordinates for the model component.

        This is a do-nothing function and should be re-implemented by
        each derived class.

        Arguments
        ---------
        size : float
            The number of sky coordinate pairs to be generated.
        """
        pass

    def __str__(self):
        """String formatting.
        """
        text = '%s %s (id = %s)'%\
               (self.__class__.__name__, self.name, self.identifier)
        text += '\n    Validity time: [%f--%f]'  %\
                (self.min_time, self.max_time)
        text += '\n    Position: RA = %s deg, Dec = %s deg' %\
                (self.ra, self.dec)
        return text

    def rvs_event_list(self, aeff, psf, modf, edisp, sampling_time):
        count_spectrum = xCountSpectrum(self.spectrum, aeff, sampling_time)
        num_events = numpy.random.poisson(count_spectrum.light_curve.norm())
        col_time = count_spectrum.light_curve.rvs(num_events)
        col_time.sort()
        event_list = xMonteCarloEventList()
        event_list.set_column('TIME', col_time)
        col_mc_energy = count_spectrum.rvs(col_time)
        event_list.set_column('MC_ENERGY', col_mc_energy)
        col_pha = edisp.matrix.rvs(col_mc_energy)
        event_list.set_column('PHA', col_pha)
        event_list.set_column('ENERGY', edisp.ebounds(col_pha))
        col_mc_ra, col_mc_dec = self.rvs_sky_coordinates(num_events)
        event_list.set_column('MC_RA', col_mc_ra)
        event_list.set_column('MC_DEC', col_mc_dec)
        col_ra, col_dec = psf.smear(col_mc_ra, col_mc_dec)
        event_list.set_column('RA', col_ra)
        event_list.set_column('DEC', col_dec)
        polarization_degree = self.polarization_degree(col_mc_energy, col_time)
        polarization_angle = self.polarization_angle(col_mc_energy, col_time)
        col_pe_angle = modf.rvs_phi(col_mc_energy, polarization_degree,
                                    polarization_angle)
        event_list.set_column('PE_ANGLE', col_pe_angle)
        event_list.set_column('MC_SRC_ID', self.identifier)
        return event_list


class xPointSource(xModelComponentBase):

    """Class representing a point source.

    Arguments
    ---------
    name : string
        The name of the source.

    ra : float
        The right ascention of the source.

    dec : float
        The declination of the source.
    """

    def __init__(self, name, ra, dec, min_time=0., max_time=1000000.):
        """Constructor.
        """
        xModelComponentBase.__init__(self, name, None, min_time, max_time)
        self.ra = ra
        self.dec = dec

    def rvs_sky_coordinates(self, size=1):
        """Generate random coordinates for the model component.

        This is returning an array of the proper length with identical values.

        Arguments
        ---------
        size : float
            The number of sky coordinate pairs to be generated.
        """
        ra = numpy.zeros(size)
        ra.fill(self.ra)
        dec = numpy.zeros(size)
        dec.fill(self.dec)
        return (ra, dec)


class xUniformDisk(xModelComponentBase):

    """Class representing a uniform disk.

    Arguments
    ---------
    name : string
        The name of the source.

    ra : float
        The right ascention of the disk center.

    dec : float
        The declination of the disk center.

    radius : float
        The radius of the disk.
    """

    def __init__(self, name, ra, dec, radius, min_time=0., max_time=1000000.):
        """Constructor.
        """
        xModelComponentBase.__init__(self, name, None, min_time, max_time)
        self.ra = ra
        self.dec = dec
        self.radius = radius

    def rvs_sky_coordinates(self, size=1):
        """Generate random coordinates for the model component.

        This is returning an array of the proper length with identical values.

        The algorithm is taken from
        http://mathworld.wolfram.com/DiskPointPicking.html

        Arguments
        ---------
        size : float
            The number of sky coordinate pairs to be generated.
        """
        r = self.radius*numpy.sqrt(numpy.random.sample(size))
        theta = numpy.random.uniform(0, 2*numpy.pi, size)
        ra = self.ra + r*numpy.cos(theta)
        dec = self.dec + r*numpy.sin(theta)
        return (ra, dec)

    def __str__(self):
        """String formatting.
        """
        text = xModelComponentBase.__str__(self)
        text += '\n    Radius: %s deg' % self.radius
        return text


class xGaussianDisk(xModelComponentBase):

    """Class representing a (azimuthally simmetric) gaussian disk.

    Arguments
    ---------
    name : string
        The name of the source.

    ra : float
        The right ascention of the disk center.

    dec : float
        The declination of the disk center.

    sigma : float
        The root mean square of the disk.
    """

    def __init__(self, name, ra, dec, sigma, min_time=0., max_time=1000000.):
        """Constructor.
        """
        xModelComponentBase.__init__(self, name, None, min_time, max_time)
        self.ra = ra
        self.dec = dec
        self.sigma = sigma
        self.__mean = [self.ra, self.dec]
        self.__cov = [[sigma**2., 0.], [0., sigma**2.]]

    def rvs_sky_coordinates(self, size=1):
        """Generate random coordinates for the model component.

        This is returning an array of the proper length with identical values.

        Arguments
        ---------
        size : float
            The number of sky coordinate pairs to be generated.
        """
        rvs = numpy.random.multivariate_normal(self.__mean, self.__cov, size)
        ra, dec = rvs[:,0], rvs[:,1]
        return (ra, dec)

    def __str__(self):
        """String formatting.
        """
        text = xModelComponentBase.__str__(self)
        text += '\n    Sigma: %s deg' % self.sigma
        return text


class xExtendedSource(xModelComponentBase):

    """Class representing an extended source.

    Arguments
    ---------
    name : string
        The name of the source.

    img_file_path : string
        The path to the FITS file containing the image of the source.
    """

    def __init__(self, name, img_file_path, min_time=0., max_time=1000000.):
        """Constructor.
        """
        xModelComponentBase.__init__(self, name, None, min_time, max_time)
        self.image = xFITSImage(img_file_path)

    def rvs_sky_coordinates(self, size=1):
        """Generate random coordinates for the model component.

        Arguments
        ---------
        size : float
            The number of sky coordinate pairs to be generated.
        """
        return self.image.rvs_coordinates(size)


class xROIModel(OrderedDict):

    """Class describing a full ROI (region of interest) model.

    This is essentially an (ordered) collection of component objects
    (i.e., instances of classes inheriting from xModelComponentBase)
    than can be accessed by source name.

    Arguments
    ---------
    ra_center : float
        The right ascention of the center of the ROI (in degrees).

    dec_center : float
        The declination of the center of the ROI (in degrees).
    """

    def __init__(self, ra_center, dec_center):
        """Constructor.
        """
        OrderedDict.__init__(self)
        self.ra = ra_center
        self.dec = dec_center

    def add_source(self, source):
        """Add a source to the ROI.
        """
        source.identifier = len(self)
        self[source.name] = source

    def add_sources(self, *sources):
        """Add an arbitrary number of sources to the ROI.
        """
        for source in sources:
            self.add_source(source)

    def min_time(self):
        """Return the minimum validity time for the ROI model.
        """
        return max([source.min_time for source in self.values()])

    def max_time(self):
        """Return the maximum validity time for the ROI model.
        """
        return min([source.max_time for source in self.values()])

    def __str__(self):
        """String formatting.
        """
        txt = 'ROI centered at (%.4f, %.4f):\n' % (self.ra, self.dec)
        for source in self.values():
            txt += '- %s\n' % source
        return txt.strip('\n')

    def build_hdu(self):
        """Build a FITS HDU for the source model.

        This can be used to be written in the output file.
        """
        pass

    def rvs_event_list(self, aeff, psf, modf, edisp, sampling_time):
        """Extract an event list for the full ROI.

        Arguments
        ---------
        aeff : :py:class:`ximpol.irf.arf.xEffectiveArea` object.
            The effective area to be used.

        psf : :py:class:`ximpol.irf.psf.xPointSpreadFunction` object.
            The PSF to be used.

        modf : :py:class:`ximpol.irf.mrf.xModulationFactor` object.
            The modulation factor to the used.

        edisp : :py:class:`ximpol.irf.rmf.xEnergyDispersion` object.
            The energy dispersion to be used.

        sampling_time : array
            The array to sample the source light curve.

        Warning
        -------
        The sampling_time should not be the same for all sources, and each
        source should be able to decide its own in a sensible way.
        (See issue #44.)
        """
        event_list = xMonteCarloEventList()
        for source in self.values():
            event_list += source.rvs_event_list(aeff, psf, modf, edisp,
                                                sampling_time)
        event_list.sort()
        return event_list


def main():
    """
    """
    model = xROIModel(0., 0.)
    src1 = xPointSource('Source 1', 0.01, 0.01, min_time=0., max_time=100.)
    src2 = xPointSource('Source 2', -0.01, -0.01, min_time=20., max_time=500.)
    print(src1)
    print(src2)
    model.add_source(src1)
    model.add_source(src2)
    print(model)
    print(model.min_time(), model.max_time())


if __name__ == '__main__':
    main()