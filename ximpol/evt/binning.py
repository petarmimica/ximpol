#!/usr/bin/env python
#
# Copyright (C) 2015--2016, the ximpol team.
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


"""Module encapsulating the FITS spectra structure and related facilities.
"""

import numpy
from astropy.io import fits
from astropy import wcs

from ximpol.utils.logging_ import logger, abort
from ximpol.evt.event import xEventFile
from ximpol.core.fitsio import xPrimaryHDU, xBinTableHDUBase
from ximpol.irf.mrf import xAzimuthalResponseGenerator
from ximpol.utils.matplotlib_ import pyplot as plt
from ximpol.srcmodel.img import xFITSImage


class xEventBinningBase:

    """Base class for the event binning.
    """

    def __init__(self, file_path, **kwargs):
        """Constructor.
        """
        self.event_file = xEventFile(file_path)
        self.event_data = self.event_file.event_data
        self.kwargs = kwargs
        self.process_kwargs()

    def get(self, key, default=None):
        """Convenience method to address the keyword aguments.
        """
        return self.kwargs.get(key, default)

    def set(self, key, value):
        """Convenience method to set keyword arguments.
        """
        logger.info('Setting %s to %s...' % (key, value))
        self.kwargs[key] = value

    def build_primary_hdu(self):
        """Build the primary HDU for the output file.
        """
        primary_hdu = xPrimaryHDU()
        primary_hdu.setup_header(self.event_file.primary_keywords())
        primary_hdu.add_keyword('BINALG', self.get('algorithm'),
                                'the binning algorithm used')
        primary_hdu.add_comment('%s run with kwargs %s' %\
                                (self.__class__.__name__, self.kwargs))
        return primary_hdu

    @classmethod
    def read_binning(self, file_path):
        """Read a custom binning from file and return a numpy array.
        """
        return numpy.loadtxt(file_path)

    @classmethod
    def bin_centers(self, bin_edges):
        """Return an array of bin centers given an array of bin edges.

        Arguments
        ---------
        bin_edges : 1-d array of length (n + 1).
            The array with the bin edges.

        Returns
        -------
        1-d array of length n.
            The array with the values of the bin centers.
        """
        assert bin_edges.ndim == 1
        return 0.5*(bin_edges[:-1] + bin_edges[1:])

    @classmethod
    def bin_widths(self, bin_edges):
        """Return an array of bin widths given an array of bin edges.

        Arguments
        ---------
        bin_edges : 1-d array of length (n + 1).
            The array with the bin edges.

        Returns
        -------
        1-d array of length n.
            The array with the values of the bin widths.
        """
        assert bin_edges.ndim == 1
        return (bin_edges[1:] - bin_edges[:-1])

    def process_kwargs(self):
        """Check the keyword arguments.
        """
        if self.get('outfile') is None:
            suffx = self.__class__.__name__.replace('xEventBinning', '').lower()
            evfile = self.event_file.file_path()
            outfile = evfile.replace('.fits', '_%s.fits' % suffx)
            self.set('outfile', outfile)

    def bin_(self):
        """Do-nothing method to be reimplemented in the derived classes.
        """
        pass


class xBinnedFileBase:

    """Base class for binned files.
    """

    def __init__(self, file_path):
        """Constructor.
        """
        assert(file_path.endswith('.fits'))
        logger.info('Opening input binned file %s...' % file_path)
        self.hdu_list = fits.open(file_path)
        self.hdu_list.info()

    def plot(self, *args, **kwargs):
        """Do nothing method.
        """
        logger.info('%s.plot() not implemented, yet.' % self.__class__.__name__)


class xBinTableHDUPHA1(xBinTableHDUBase):

    """Binary table for binned PHA1 data.
    """

    NAME = 'SPECTRUM'
    HEADER_KEYWORDS = [
        ('HDUCLASS', 'OGIP'),
        ('HDUCLAS1', 'SPECTRUM'),
        ('HDUCLAS2', 'TOTAL'),
        ('HDUCLAS3', 'RATE'),
        ('CHANTYPE', 'PI'),
        ('HDUVERS' , '1.2.1', 'OGIP version number'),
        ('TLMIN1'  , 0      , 'first channel number'),
        ('CORRSCAL', 1.     , 'scaling for correction file'),
        ('POISSERR', 'T'    , 'is error Poisson?'),
        ('RESPFILE', None),
        ('ANCRFILE', None),
        ('BACKFILE', None),
        ('CORRFILE', None),
        ('SYS_ERR' , 0.),
        ('AREASCAL', 1.),
        ('BACKSCAL', 1.)
    ]
    DATA_SPECS = [
        ('CHANNEL' , 'J'),
        ('RATE'    , 'E', 'counts/s'),
        ('STAT_ERR', 'E', 'counts/s'),
    ]


class xEventBinningPHA1(xEventBinningBase):

    """Class for PHA1 binning.
    """

    def process_kwargs(self):
        """Overloaded method.
        """
        xEventBinningBase.process_kwargs(self)

    def bin_(self):
        """Overloaded method.
        """
        evt_header = self.event_file.hdu_list['PRIMARY'].header
        num_chans = evt_header['DETCHANS']
        total_time = self.event_file.total_good_time()
        binning = numpy.linspace(-0.5, num_chans - 0.5, num_chans)
        n, bins = numpy.histogram(self.event_data['PHA'], bins=binning)
        primary_hdu = self.build_primary_hdu()
        data = [numpy.arange(num_chans),
                n/total_time,
                numpy.sqrt(n)/total_time
        ]
        spec_hdu = xBinTableHDUPHA1(data)
        spec_hdu.setup_header(self.event_file.primary_keywords())
        keywords = [('EXPOSURE', total_time, 'exposure time')]
        spec_hdu.setup_header(keywords)
        hdu_list = fits.HDUList([primary_hdu, spec_hdu])
        hdu_list.info()
        logger.info('Writing binned PHA1 data to %s...' % self.get('outfile'))
        hdu_list.writeto(self.get('outfile'), clobber=True)
        logger.info('Done.')


class xBinnedCountSpectrum(xBinnedFileBase):

    """Binned phasogram.
    """

    def __init__(self, file_path):
        """Constructor.
        """
        xBinnedFileBase.__init__(self, file_path)
        self.data = self.hdu_list['SPECTRUM'].data
        self.channel = self.data['CHANNEL']
        self.rate = self.data['RATE']
        self.error = self.data['STAT_ERR']

    def plot(self, show=True):
        """Overloaded plot method.
        """
        fig = plt.figure('Count spectrum')
        plt.errorbar(self.channel, self.rate, yerr=self.error, fmt='o')
        plt.xlabel('PHA')
        plt.ylabel('Rate [Hz]')
        plt.yscale('log')
        if show:
            plt.show()


class xEventBinningCMAP(xEventBinningBase):

    """Class for CMAP binning.
    """

    def process_kwargs(self):
        """Overloaded method.
        """
        xEventBinningBase.process_kwargs(self)
        primary_header = self.event_file.hdu_list['PRIMARY'].header
        if self.get('xref') is None:
            self.set('xref', primary_header['ROIRA'])
        if self.get('yref') is None:
            self.set('yref', primary_header['ROIDEC'])

    def bin_(self):
        """Overloaded method.
        """
        if self.get('mc'):
            ra = self.event_data['MC_RA']
            dec = self.event_data['MC_DEC']
        else:
            ra = self.event_data['RA']
            dec = self.event_data['DEC']
        xref = self.get('xref')
        yref = self.get('yref')
        nxpix = self.get('nxpix')
        nypix = self.get('nypix')
        pixsize = self.get('binsz')/3600.
        proj = self.get('proj')
        sidex = nxpix*pixsize
        sidey = nypix*pixsize
        logger.info('Output image dimensions are %.1f x %.1f arcmin.' %\
                    (sidex*60, sidey*60))
        binsx = numpy.linspace(0, nxpix, nxpix + 1)
        binsy = numpy.linspace(0, nypix, nypix + 1)
        # Build the WCS object
        w = wcs.WCS(naxis=2)
        w.wcs.crpix = [0.5*nxpix, 0.5*nypix]
        w.wcs.cdelt = [-pixsize, pixsize]
        w.wcs.crval = [xref, yref]
        w.wcs.ctype = ['RA---%s' % proj, 'DEC--%s' % proj]
        w.wcs.equinox = 2000.
        w.wcs.radesys = 'ICRS'
        header = w.to_header()
        # And here we need to tweak the header by hand to replicate what we
        # do in xEventBinningBase.build_primary_hdu() for the other binning
        # algorithms.
        header.set('BINALG', self.get('algorithm'),'the binning algorithm used')
        for key, val, comment in self.event_file.primary_keywords():
            header.set(key, val, comment)
        header['COMMENT'] = '%s run with kwargs %s' %\
                            (self.__class__.__name__, self.kwargs)
        # Ready to go!
        pix = w.wcs_world2pix(zip(ra, dec), 1)
        n, x, y = numpy.histogram2d(pix[:,1], pix[:,0], bins=(binsx, binsy))
        hdu = fits.PrimaryHDU(n, header=header)
        logger.info('Writing binned CMAP data to %s...' % self.get('outfile'))
        hdu.writeto(self.get('outfile'), clobber=True)
        logger.info('Done.')


class xBinnedMap:

    """Display interface to binned CMAP files.
    """

    def __init__(self, file_path):
        """Constructor.
        """
        self.image = xFITSImage(file_path, build_cdf=False)

    def plot(self, show=True,subplot=(1,1,1)):
        """Plot the data.
        """
        return self.image.plot(show=show,subplot=subplot)


class xBinTableHDULC(xBinTableHDUBase):

    """Binary table for binned LC data.
    """

    NAME = 'RATE'
    HEADER_KEYWORDS = []
    DATA_SPECS = [
        ('TIME'   , 'D', 's'     , 'time of the bin center'),
        ('TIMEDEL', 'D', 's'     , 'bin size'),
        ('COUNTS' , 'J', 'counts', 'photon counts'),
        ('ERROR'  , 'E', 'counts', 'statistical errors')
    ]


class xEventBinningLC(xEventBinningBase):

    """Class for LC binning.
    """

    def process_kwargs(self):
        """Overloaded method.
        """
        xEventBinningBase.process_kwargs(self)
        if self.get('tstart') is None:
            self.set('tstart', self.event_file.min_good_time())
        if self.get('tstop') is None:
            self.set('tstop', self.event_file.max_good_time())

    def make_binning(self):
        """Build the light-curve binning.
        """
        tbinalg = self.get('tbinalg')
        tstart = self.get('tstart')
        tstop = self.get('tstop')
        tbins = self.get('tbins')
        if tbinalg == 'LIN':
            return numpy.linspace(tstart, tstop, tbins + 1)
        elif tbinalg == 'LOG':
            return numpy.linspace(numpy.log10(tstart), numpy.log10(tstop),
                                  tbins + 1)
        elif tbinalg == 'FILE':
            tbinfile = self.get('tbinfile')
            assert tbinfile is not None
            return self.read_binning(tbinfile)
        abort('tbinalg %s not implemented yet' % tbinalg)

    def bin_(self):
        """Overloaded method.
        """
        evt_header = self.event_file.hdu_list['PRIMARY'].header
        counts, edges = numpy.histogram(self.event_data['TIME'],
                                        bins=self.make_binning())
        primary_hdu = self.build_primary_hdu()
        data = [self.bin_centers(edges),
                self.bin_widths(edges),
                counts,
                numpy.sqrt(counts)
        ]
        rate_hdu = xBinTableHDULC(data)
        rate_hdu.setup_header(self.event_file.primary_keywords())
        gti_hdu = self.event_file.hdu_list['GTI']
        hdu_list = fits.HDUList([primary_hdu, rate_hdu, gti_hdu])
        hdu_list.info()
        logger.info('Writing binned LC data to %s...' % self.get('outfile'))
        hdu_list.writeto(self.get('outfile'), clobber=True)
        logger.info('Done.')


class xBinnedLightCurve(xBinnedFileBase):

    """Binned light curve.
    """

    def __init__(self, file_path):
        """Constructor.
        """
        xBinnedFileBase.__init__(self, file_path)
        self.data = self.hdu_list['RATE'].data
        self.time = self.data['TIME']
        self.counts = self.data['COUNTS']
        self.error = self.data['ERROR']

    def plot(self, show=True):
        """Overloaded plot method.
        """
        fig = plt.figure('Light curve')
        plt.errorbar(self.time, self.counts, yerr=self.error, fmt='o')
        plt.xlabel('Time [s]')
        plt.ylabel('Counts/bin')
        if show:
            plt.show()


class xBinTableHDUPHASG(xBinTableHDUBase):

    """Binary table for binned PHASG data.
    """

    NAME = 'RATE'
    HEADER_KEYWORDS = []
    DATA_SPECS = [
        ('PHASE'   , 'D', 's'     , 'phase of the bin center'),
        ('PHASEDEL', 'D', 's'     , 'phase bin size'),
        ('COUNTS'  , 'J', 'counts', 'photon counts'),
        ('ERROR'   , 'E', 'counts', 'statistical errors')
    ]


class xEventBinningPHASG(xEventBinningBase):

    """Class for LC binning.
    """

    def process_kwargs(self):
        """Overloaded method.
        """
        xEventBinningBase.process_kwargs(self)

    def make_binning(self):
        """Build the light-curve binning.
        """
        phasebins = self.get('phasebins')
        return numpy.linspace(0., 1., phasebins + 1)

    def bin_(self):
        """Overloaded method.
        """
        evt_header = self.event_file.hdu_list['PRIMARY'].header
        counts, edges = numpy.histogram(self.event_data['PHASE'],
                                        bins=self.make_binning())
        primary_hdu = self.build_primary_hdu()
        data = [self.bin_centers(edges),
                self.bin_widths(edges),
                counts,
                numpy.sqrt(counts)
        ]
        rate_hdu = xBinTableHDUPHASG(data)
        rate_hdu.setup_header(self.event_file.primary_keywords())
        gti_hdu = self.event_file.hdu_list['GTI']
        hdu_list = fits.HDUList([primary_hdu, rate_hdu, gti_hdu])
        hdu_list.info()
        logger.info('Writing binned PHASG data to %s...' % self.get('outfile'))
        hdu_list.writeto(self.get('outfile'), clobber=True)
        logger.info('Done.')


class xBinnedPhasogram(xBinnedFileBase):

    """Binned phasogram.
    """

    def __init__(self, file_path):
        """Constructor.
        """
        xBinnedFileBase.__init__(self, file_path)
        self.data = self.hdu_list['RATE'].data
        self.phase = self.data['PHASE']
        self.counts = self.data['COUNTS']
        self.error = self.data['ERROR']

    def plot(self, show=True):
        """Overloaded plot method.
        """
        fig = plt.figure('Phasogram')
        plt.errorbar(self.phase, self.counts, yerr=self.error, fmt='o')
        plt.xlabel('Phase')
        plt.ylabel('Counts/bin')
        if show:
            plt.show()


class xBinTableHDUMCUBE(xBinTableHDUBase):

    """Binary table for binned MCUBE data.

    Mind the field for the actual phi distribution depends on the binning,
    which is specified at run time, and therefore the corresponding data specs
    must be set dinamically.
    """

    NAME = 'MODULATION'
    HEADER_KEYWORDS = []
    DATA_SPECS = [
        ('ENERGY_LO'  , 'E', 'keV'),
        ('ENERGY_HI'  , 'E', 'keV'),
        ('ENERGY_MEAN', 'E', 'keV')
    ]

    @classmethod
    def add_phi_spec(self, phibins):
        """Add the specification for the PHIHIST field.
        """
        phi_specs = ('PHI_HIST', '%dJ' % phibins)
        self.DATA_SPECS.append(phi_specs)


class xEventBinningMCUBE(xEventBinningBase):

    """Class for MCUBE binning.
    """

    def process_kwargs(self):
        """Overloaded method.
        """
        xEventBinningBase.process_kwargs(self)

    def make_binning(self):
        """Build the modulation cube binning.
        """
        ebinalg = self.get('ebinalg')
        emin = self.get('emin')
        emax = self.get('emax')
        ebins = self.get('ebins')
        if ebinalg == 'LIN':
            ebinning = numpy.linspace(emin, emax, ebins + 1)
        elif ebinalg == 'LOG':
            ebinning = numpy.linspace(numpy.log10(emin), numpy.log10(emax),
                                      ebins + 1)
        elif ebinalg == 'EQP':
            if self.get('mc'):
                energy = numpy.copy(self.event_data['MC_ENERGY'])
            else:
                energy = numpy.copy(self.event_data['ENERGY'])
            mask = (energy > self.get('emin'))*(energy < self.get('emax'))
            energy = energy[mask]
            energy.sort()
            ebinning = [emin]
            for i in range(1, ebins):
                index = int(i*len(energy)/float(ebins))
                ebinning.append(energy[index])
            ebinning.append(emax)
            ebinning = numpy.array(ebinning)
        elif ebinalg == 'FILE':
            ebinfile = self.get('ebinfile')
            assert ebinfile is not None
            ebinning = self.read_binning(ebinfile)
        else:
            abort('ebinalg %s not implemented yet' % ebinalg)
        phibinning = numpy.linspace(0, 2*numpy.pi, self.get('phibins') + 1)
        return (ebinning, phibinning)

    def bin_(self):
        """Overloaded method.
        """
        evt_header = self.event_file.hdu_list['PRIMARY'].header
        if self.get('mc'):
            energy = self.event_data['MC_ENERGY']
        else:
            energy = self.event_data['ENERGY']
        phi = self.event_data['PE_ANGLE']
        counts, xedges, yedges = numpy.histogram2d(energy, phi,
                                                   bins=self.make_binning())
        primary_hdu = self.build_primary_hdu()
        emin, emax = xedges[:-1], xedges[1:]
        emean = []
        for _emin, _emax in zip(emin, emax):
            emean.append(numpy.mean(energy[(energy > _emin)*(energy < _emax)]))
        data = [emin, emax, emean, counts]
        xBinTableHDUMCUBE.add_phi_spec(self.get('phibins'))
        mcube_hdu = xBinTableHDUMCUBE(data)
        mcube_hdu.setup_header(self.event_file.primary_keywords())
        gti_hdu = self.event_file.hdu_list['GTI']
        hdu_list = fits.HDUList([primary_hdu, mcube_hdu, gti_hdu])
        hdu_list.info()
        logger.info('Writing binned MCUBE data to %s...' % self.get('outfile'))
        hdu_list.writeto(self.get('outfile'), clobber=True)
        logger.info('Done.')


class xBinnedModulationCube(xBinnedFileBase):

    """Read-mode interface to a MCUBE FITS file.
    """

    def __init__(self, file_path):
        """Constructor.
        """
        xBinnedFileBase.__init__(self, file_path)
        self.data = self.hdu_list['MODULATION'].data
        self.emin = self.data['ENERGY_LO']
        self.emax = self.data['ENERGY_HI']
        self.emean = self.data['ENERGY_MEAN']
        self.phi_y = self.data['PHI_HIST']
        phibins = self.phi_y.shape[1]
        self.phi_binning = numpy.linspace(0, 2*numpy.pi, phibins + 1)
        self.phi_x = 0.5*(self.phi_binning[:-1] + self.phi_binning[1:])

    def fit_bin(self, i):
        """Fit the azimuthal distribution for the i-th energy slice.
        """
        hist = (self.phi_y[i], self.phi_binning, None)
        fit_results = xAzimuthalResponseGenerator.fit_histogram(hist)
        logger.info(fit_results)
        return fit_results

    def plot_bin(self, i, show=True, fit=True):
        """Plot the azimuthal distribution for the i-th energy slice.
        """
        _emin = self.emin[i]
        _emax = self.emax[i]
        _emean = self.emean[i]
        label = '%.2f$--$%.2f $<$%.3f$>$ keV' % (_emin, _emax, _emean)
        #if fig is None: fig = plt.figure('Modulation curve (%s)' % label)
        plt.errorbar(self.phi_x, self.phi_y[i], yerr=numpy.sqrt(self.phi_y[i]),
                     fmt='o')
        if fit:
            fit_results = self.fit_bin(i)
            fit_results.plot()
        plt.axis([0., 2*numpy.pi, 0., 1.2*self.phi_y[i].max()])
        plt.xlabel('Azimuthal angle [rad]')
        plt.ylabel('Counts/bin')
        plt.text(0.02, 0.95, label, transform=plt.gca().transAxes)
        if show:
            plt.show()

    def plot(self, show=True, fit=True, analyze=True,xsubplot=0):
        """Plot the azimuthal distributions for all the energy bins.
        """
        if analyze:
            fit = True
        fit_results = []
        if xsubplot==0: plt.figure()
        for i, _emean in enumerate(self.emean):
            plt.subplot(len(self.emean),xsubplot+1,(xsubplot+1)*(i+1))
            self.plot_bin(i, False, False)
            if fit:
                _res = self.fit_bin(i)
                _res.plot()
                fit_results.append(_res)
        if analyze:
            from ximpol.irf import load_mrf
            irf_name = self.hdu_list['PRIMARY'].header['IRFNAME']
            modf = load_mrf(irf_name)
            fig = plt.figure('Polarization degree vs. energy')
            _x = self.emean
            _y = numpy.array([_res.visibility for _res in fit_results])
            _y /= modf(_x)
            _dy = numpy.array([_res.visibility_error for _res in fit_results])
            _dy /= modf(_x)
            plt.errorbar(_x, _y, _dy, fmt='o')
            plt.xlabel('Energy [keV]')
            plt.ylabel('Polarization degree')
            fig = plt.figure('Polarization angle vs. energy')
            _y = [numpy.degrees(_res.phase) for _res in fit_results]
            _dy = [numpy.degrees(_res.phase_error) for _res in fit_results]
            plt.errorbar(_x, _y, _dy, fmt='o')
            plt.xlabel('Energy [keV]')
            plt.ylabel('Polarization angle [$^\circ$]')
        if show:
            plt.show()
