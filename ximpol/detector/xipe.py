#!/usr/bin/env python
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


import os
import numpy

from scipy import stats
from astropy.io import fits

from ximpol import XIMPOL_DETECTOR, XIMPOL_IRF
from ximpol.utils.logging_ import logger
from ximpol.utils.os_ import rm
from ximpol.core.spline import xInterpolatedUnivariateSplineLinear
from ximpol.core.fitsio import xPrimaryHDU
from ximpol.irf.arf import xBinTableHDUSPECRESP
from ximpol.irf.mrf import xBinTableHDUMODFRESP
from ximpol.irf.psf import xBinTableHDUPSF
from ximpol.irf.rmf import xBinTableHDUMATRIX, xBinTableHDUEBOUNDS


def _full_path(file_name):
    return os.path.join(XIMPOL_DETECTOR, 'data', file_name)

"""Energy bounds and sampling for the actual IRFs.
"""
ENERGY_MIN = 0.1            # keV
ENERGY_MAX = 11.0           # keV
ENERGY_STEP = 0.01          # keV
ENERGY_LO = numpy.arange(ENERGY_MIN, ENERGY_MAX, ENERGY_STEP)
ENERGY_HI = numpy.append(ENERGY_LO[1:], ENERGY_MAX)
ENERGY_CENTER = 0.5*(ENERGY_LO + ENERGY_HI)

"""Detector characteristics for the XIPE baseline configuration.
"""
GAS_MIXTURE = 'Ne/DME 80/20'#
GAS_PRESSURE = 1.           # Atm
ABS_GAP_THICKNESS = 1.      # cm
QUAL_CUT_EFFICIENCY = 0.8   #
WINDOW_MATERIAL = 'Be'      #
WINDOW_THICKNESS = 50.      # um
NUM_CHANNELS = 256          #
E_CHAN_OFFSET = 0.          # keV
E_CHAN_SLOPE = ENERGY_MAX/float(NUM_CHANNELS) # keV/channel

"""PSF parameters.

Taken directly from http://arxiv.org/abs/1403.7200, table 2, @4.51 keV.
"""
PSF_PARAMETERS = [numpy.array([_x]) for _x in \
                  [2.79e-4, 10.61, 3.289e-3, 6.06, 1.481]]

"""XIPE-specific fields for the FITS headers. (These will be added to the
generic headers defined for the various extensions in the irf modules.)
"""
XIPE_KEYWORDS = [
    ('TELESCOP', 'XIPE' , 'mission/satellite name'),
    ('INSTRUME', 'GPD'  , 'instrument/detector name'),
    ('DETNAM'  , 'ALL'  , 'specific detector name in use')
]

"""Comments fields for the FITS headers.
"""
XIPE_COMMENTS = [
    'Gas mixture: %s' % GAS_MIXTURE,
    'Pressure: %.3f Atm' % GAS_PRESSURE,
    'Absorption gap: %.3f cm' % ABS_GAP_THICKNESS,
    'Quality cut efficiency: %.3f' % QUAL_CUT_EFFICIENCY,
    'Window: %s, %d um' % (WINDOW_MATERIAL, WINDOW_THICKNESS)
]


def make_arf(aeff_file_path, qeff_file_path, irf_name):
    """Write the XIPE effective area response function.
    """
    logger.info('Creating XIPE effective area fits file...')
    output_file_name = '%s.arf' % irf_name
    output_file_path = os.path.join(XIMPOL_IRF, 'fits', output_file_name)
    if os.path.exists(output_file_path):
        rm(output_file_path)
    logger.info('Loading mirror effective area from %s...' % aeff_file_path)
    _x, _y = numpy.loadtxt(aeff_file_path, unpack=True)
    opt_aeff = xInterpolatedUnivariateSplineLinear(_x, _y)
    logger.info('Loading quantum efficiency from %s...' % qeff_file_path)
    _x, _y = numpy.loadtxt(qeff_file_path, unpack=True)
    gpd_eff = xInterpolatedUnivariateSplineLinear(_x, _y)
    aeff = opt_aeff*gpd_eff
    specresp = aeff(ENERGY_CENTER)
    logger.info('Creating PRIMARY HDU...')
    primary_hdu = xPrimaryHDU('ximpol', XIPE_KEYWORDS, XIPE_COMMENTS)
    print(repr(primary_hdu.header))
    logger.info('Creating SPECRESP HDU...')
    data = [ENERGY_LO, ENERGY_HI, specresp]
    specresp_hdu = xBinTableHDUSPECRESP(data, XIPE_KEYWORDS, XIPE_COMMENTS)
    print(repr(specresp_hdu.header))
    logger.info('Writing output file %s...' % output_file_path)
    hdulist = fits.HDUList([primary_hdu, specresp_hdu])
    hdulist.info()
    hdulist.writeto(output_file_path)
    logger.info('Done.')


def make_mrf(modf_file_path, irf_name):
    """Write the XIPE modulation factor response function.
    """
    logger.info('Creating XIPE effective area fits file...')
    output_file_name = '%s.mrf' % irf_name
    output_file_path = os.path.join(XIMPOL_IRF, 'fits', output_file_name)
    if os.path.exists(output_file_path):
        rm(output_file_path)
    logger.info('Loading modulation factor from %s...' % modf_file_path)
    _x, _y = numpy.loadtxt(modf_file_path, unpack=True)
    modf = xInterpolatedUnivariateSplineLinear(_x, _y)
    logger.info('Filling in arrays...')
    modfresp = modf(ENERGY_CENTER)
    logger.info('Creating PRIMARY HDU...')
    primary_hdu = xPrimaryHDU('ximpol', XIPE_KEYWORDS, XIPE_COMMENTS)
    print(repr(primary_hdu.header))
    logger.info('Creating MODFRESP HDU...')
    data = [ENERGY_LO, ENERGY_HI, modfresp]
    modfresp_hdu = xBinTableHDUMODFRESP(data, XIPE_KEYWORDS, XIPE_COMMENTS)
    print(repr(modfresp_hdu.header))
    logger.info('Writing output file %s...' % output_file_path)
    hdulist = fits.HDUList([primary_hdu, modfresp_hdu])
    hdulist.info()
    hdulist.writeto(output_file_path)
    logger.info('Done.')


def make_psf(irf_name):
    """Write the XIPE PSF parameters.
    """
    logger.info('Creating XIPE effective area fits file...')
    output_file_name = '%s.psf' % irf_name
    output_file_path = os.path.join(XIMPOL_IRF, 'fits', output_file_name)
    if os.path.exists(output_file_path):
        rm(output_file_path)
    logger.info('Creating PRIMARY HDU...')
    primary_hdu = xPrimaryHDU('ximpol', XIPE_KEYWORDS, XIPE_COMMENTS)
    print(repr(primary_hdu.header))
    logger.info('Creating PSF HDU...')
    data = PSF_PARAMETERS
    psf_hdu = xBinTableHDUPSF(data, [], XIPE_COMMENTS)
    print(repr(psf_hdu.header))
    logger.info('Writing output file %s...' % output_file_path)
    hdulist = fits.HDUList([primary_hdu, psf_hdu])
    hdulist.info()
    hdulist.writeto(output_file_path)
    logger.info('Done.')


def make_rmf(eres_file_path, irf_name):
    """Write the XIPE edisp response function.

    The specifications are describes at page ~15 of the following document:
    ftp://legacy.gsfc.nasa.gov/caldb/docs/memos/cal_gen_92_002/cal_gen_92_002.ps
    """
    output_file_name = '%s.rmf' % irf_name
    output_file_path = os.path.join(XIMPOL_IRF, 'fits', output_file_name)
    if os.path.exists(output_file_path):
        rm(output_file_path)
    logger.info('Loading energy dispersion from %s...' % eres_file_path)
    _x, _y = numpy.loadtxt(eres_file_path, unpack=True)
    edisp_fwhm = xInterpolatedUnivariateSplineLinear(_x, _y)
    logger.info('Creating PRIMARY HDU...')
    primary_hdu = xPrimaryHDU('ximpol', XIPE_KEYWORDS, XIPE_COMMENTS)
    print(repr(primary_hdu.header))
    keyword = ('DETCHANS', NUM_CHANNELS, 'Total number of detector channels')
    rmf_header_keywords = XIPE_KEYWORDS + [keyword]
    logger.info('Creating MATRIX HDU...')
    nrows = len(ENERGY_LO)
    ngrp = numpy.ones(nrows)
    fchan = numpy.zeros(nrows)
    nchan = numpy.array([NUM_CHANNELS]*nrows, 'i')
    matrix = numpy.zeros((0, NUM_CHANNELS))
    ch = numpy.arange(NUM_CHANNELS)
    for energy, rms in zip(ENERGY_CENTER, edisp_fwhm(ENERGY_CENTER)/2.358):
        mean_chan = int((energy - E_CHAN_OFFSET)/E_CHAN_SLOPE)
        rms_chan = rms/E_CHAN_SLOPE
        rv = stats.norm(loc=mean_chan, scale=rms_chan)
        matrix = numpy.vstack([matrix, rv.pdf(ch)])
    data = [ENERGY_LO, ENERGY_HI, ngrp, fchan, nchan, matrix]
    matrix_hdu = xBinTableHDUMATRIX(NUM_CHANNELS, data, rmf_header_keywords,
                                    XIPE_COMMENTS)
    print(repr(matrix_hdu.header))
    logger.info('Creating EBOUNDS HDU...')
    ch = numpy.arange(NUM_CHANNELS)
    emin = ch*E_CHAN_SLOPE + E_CHAN_OFFSET
    emax = (ch + 1)*E_CHAN_SLOPE + E_CHAN_OFFSET
    data = [ch, emin, emax]
    ebounds_hdu = xBinTableHDUEBOUNDS(data, rmf_header_keywords, XIPE_COMMENTS)
    print(repr(ebounds_hdu.header))
    logger.info('Writing output file %s...' % output_file_path)
    hdulist = fits.HDUList([primary_hdu, matrix_hdu, ebounds_hdu])
    hdulist.info()
    hdulist.writeto(output_file_path)
    logger.info('Done.')


def make_all():
    """Create all the XIPE response functions.
    """
    # Effective area.
    aeff_file_path = _full_path('Area_XIPE_201602b_x3.asc')
    qeff_file_path = _full_path('eff_hedme8020_1atm_1cm_cuts80p_be50um_p_x.asc')
    make_arf(aeff_file_path, qeff_file_path, 'xipe_baseline')
    aeff_file_path = _full_path('Area_XIPE_201602g_x3.asc')
    make_arf(aeff_file_path, qeff_file_path, 'xipe_goal')
    # Energy dispersion.
    eres_file_path = _full_path('eres_fwhm_hedme8020_1atm_1cm.asc')
    make_rmf(eres_file_path, 'xipe_baseline')
    make_rmf(eres_file_path, 'xipe_goal')
    # Modulation factor.
    modf_file_path = _full_path('modfact_hedme8020_1atm_1cm_mng.asc')
    make_mrf(modf_file_path, 'xipe_baseline')
    make_mrf(modf_file_path, 'xipe_goal')
    # Point-spread function.
    make_psf('xipe_baseline')
    make_psf('xipe_goal')


if __name__ == '__main__':
    make_all()
