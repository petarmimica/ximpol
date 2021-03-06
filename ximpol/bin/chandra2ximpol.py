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


__description__ = 'Chandra-to-ximpol converter'


import os
import numpy
import imp

from astropy import wcs
from astropy.io import fits
from ximpol.irf import load_irfs
from ximpol.utils.os_ import mkdir
from ximpol.utils.profile import xChrono
from ximpol import XIMPOL_IRF, XIMPOL_DATA
from ximpol.srcmodel.roi import xROIModel
from ximpol.srcmodel.polarization import constant
from ximpol.evt.event import xMonteCarloEventList
from ximpol.utils.logging_ import logger, startmsg, abort
from ximpol.core.spline import xInterpolatedUnivariateSplineLinear

"""Command-line switches.
"""
import ast
import argparse

formatter = argparse.ArgumentDefaultsHelpFormatter
PARSER = argparse.ArgumentParser(description=__description__,
                                 formatter_class=formatter)
PARSER.add_argument('evfile', type=str,
                    help='path to the input FITS event file')
PARSER.add_argument('--outfile', type=str, default=None,
                    help='the output FITS event file')
PARSER.add_argument('--configfile', type=str, default=None,
                    help='the input configuration file')
PARSER.add_argument('--duration', type=float, default=numpy.nan,
                    help='the duration (in s) of the simulation')
PARSER.add_argument('--irfname', type=str, default='xipe_baseline',
                    help='the input configuration file')
PARSER.add_argument('--acis', type=str, default='i', choices=['i', 's'],
                    help='the chandra acis detector name')
PARSER.add_argument('--seed', type=int, default=0,
                    help='the random seed for the simulation')
PARSER.add_argument('--clobber', type=ast.literal_eval, choices=[True, False],
                    default=True,
                    help='overwrite or do not overwrite existing output files')
                    
class xSimulationInfo:

    """Empty container to pass along all the relevant information about the
    simulation.
    """

    pass

def _get_radec(hdr, tbdata):
    """Make the conversion from pixel coordinates to Ra-Dec.
    """
    # Read wcs parameters from header.
    index = hdr.values().index('EQPOS')
    wcs_list = hdr[index+2:index+11].values()

    # Create and set up a WCS object.
    w = wcs.WCS(naxis=2)
    w.wcs.crpix = wcs_list[2:8:5]
    w.wcs.cdelt = numpy.array(wcs_list[3:9:5])
    w.wcs.crval = wcs_list[1:7:5]
    w.wcs.ctype = wcs_list[0:6:5]
    w.wcs.equinox = 2000.
    w.wcs.radesys = 'ICRS'

    # Read the pixel coordinates to be converted.
    x = tbdata['x']
    y = tbdata['y']
    pixcrd = numpy.column_stack((x,y))

    # Convert pixel coordinates to world coordinates (Ra, Dec).
    ra_dec = w.wcs_pix2world(pixcrd, 1)
    return ra_dec[:,0], ra_dec[:,1]
    
def load_chandra_arf(arf_file):
    """Load the Chandra effective area data
    """
    hdu_list = fits.open(arf_file)
    tbdata = hdu_list['SPECRESP'].data
    _x = 0.5*(tbdata.field('ENERG_LO') + tbdata.field('ENERG_HI'))
    _y = tbdata.field('SPECRESP')
    fmt = dict(xname='Energy', xunits='keV', yname='Effective area',
               yunits='cm$^2$')
    return xInterpolatedUnivariateSplineLinear(_x, _y, **fmt)

def time_scaling(scale, col_mc_energy, col_time, col_mc_ra, col_mc_dec):
    """Make the scaling from Chandra observation time to an arbitrary time
    provided with duration parameter.
    """
    mc_energy = numpy.array([])
    time = numpy.array([])
    mc_ra = numpy.array([])
    mc_dec = numpy.array([])
    delta_time = col_time[-1]-col_time[0]
    for i in range(0, int(scale[1])):
        mc_energy = numpy.append(mc_energy, col_mc_energy)
        time = numpy.append(time, i*delta_time + col_time)
        mc_ra = numpy.append(mc_ra, col_mc_ra)
        mc_dec = numpy.append(mc_dec, col_mc_dec)
    index = 1+int(scale[0]*len(col_mc_energy))
    mc_energy = numpy.append(mc_energy, col_mc_energy[:index])
    time = numpy.append(time, (i+1)*delta_time + col_time[:index])
    mc_ra = numpy.append(mc_ra, col_mc_ra[:index])
    mc_dec = numpy.append(mc_dec, col_mc_dec[:index])    
    return mc_energy, time, mc_ra, mc_dec
    
def chandra2ximpol(file_path, **kwargs):
    """Make the conversion from Chandra to ximpol.
    """
    assert(file_path.endswith('.fits'))
    if kwargs['outfile'] is None:
        outfile = os.path.basename(file_path).replace('.fits','_xipe.fits')
        mkdir(XIMPOL_DATA)
        kwargs['outfile'] = os.path.join(XIMPOL_DATA, outfile)
        logger.info('Setting output file path to %s...' % kwargs['outfile'])
    if os.path.exists(kwargs['outfile']) and not kwargs['clobber']:
        logger.info('Output file %s already exists.' % kwargs['outfile'])
        logger.info('Remove the file or set "clobber = True" to overwite it.')
        return kwargs['outfile']
   
    chrono = xChrono()
    logger.info('Setting the random seed to %d...' % kwargs['seed'])
    numpy.random.seed(kwargs['seed'])   
    logger.info('Loading the instrument response functions...')
    aeff, psf, modf, edisp = load_irfs(kwargs['irfname'])   
    c_aeff_name = 'chandra_acis_%s.arf' % kwargs['acis']
    c_aeff_file = os.path.join(XIMPOL_IRF, 'fits', c_aeff_name)   
    logger.info('Reading Chandra effective area data from %s...' % c_aeff_file)    
    c_aeff = load_chandra_arf(c_aeff_file) 
    _x = aeff.x
    _y = aeff.y/c_aeff(_x)
    aeff_ratio = xInterpolatedUnivariateSplineLinear(_x, _y)
    logger.info('Loading the input FITS event file...')
    hdu_list = fits.open(file_path)
    # If configuration file is not provided we assume a non-polarized source
    if kwargs['configfile'] is None:
        logger.info('Configuration file not provided.')
        logger.info('Setting polarization angle and degree to zero...')                 
        polarization_degree = constant(0.)
        polarization_angle = constant(0.)
    else:
        logger.info('Setting up the polarization source model...')
        module_name = os.path.basename(kwargs['configfile']).replace('.py', '')
        polarization_degree = imp.load_source(module_name, 
                                    kwargs['configfile']).POLARIZATION_DEGREE
        polarization_angle = imp.load_source(module_name, 
                                    kwargs['configfile']).POLARIZATION_ANGLE
    logger.info('Done %s.' % chrono)
    
    hdr = hdu_list[1].header
    tbdata = hdu_list[1].data        
    tstart = hdr['TSTART']
    tstop = hdr['TSTOP']
    obs_time = tstop - tstart
    logger.info('Chandra observation time: %i s.' %obs_time)
    ra_pnt = hdr['RA_PNT']
    dec_pnt = hdr['DEC_PNT']
    ROI_MODEL = xROIModel(ra_pnt, dec_pnt)
    
    logger.info('Reading Chandra data...')
    col_mc_energy = tbdata['energy']*0.001 # eV -> keV
    rnd_ratio = numpy.random.random(len(col_mc_energy))
    # The condition col_mc_energy < 10. is needed to avoid to take the bunch of 
    # events with energy > 10 keV included into the Chandra photon list (we
    # actually don't know the reason).
    _mask = (rnd_ratio < aeff_ratio(col_mc_energy))*(col_mc_energy<10.)
    # This is needed for over-sample the events in case of effective area ratio
    # greater than 1.
    _mask_ratio = (rnd_ratio < (aeff_ratio(col_mc_energy)-1.))*\
                                                            (col_mc_energy<10.)
    col_mc_energy = numpy.append(col_mc_energy[_mask], 
                                                    col_mc_energy[_mask_ratio])

    col_time = numpy.append(tbdata['time'][_mask],tbdata['time'][_mask_ratio])
    col_mc_ra, col_mc_dec = _get_radec(hdr, tbdata)
    col_mc_ra = numpy.append(col_mc_ra[_mask], col_mc_ra[_mask_ratio])
    col_mc_dec = numpy.append(col_mc_dec[_mask], col_mc_dec[_mask_ratio])

    duration = kwargs['duration']
    if not numpy.isnan(duration):
        logger.info('Setting the observation time to %d s...' % duration)                             
        scale = numpy.modf(duration/obs_time)
        tstop = tstart + duration
        logger.info('Scaling counts according to observation time...')
        col_mc_energy, col_time, col_mc_ra, col_mc_dec = time_scaling(scale, 
                                col_mc_energy, col_time, col_mc_ra, col_mc_dec)
          
    logger.info('Converting from Chandra to ximpol...')
    gti_list = [(tstart, tstop)]
    event_list = xMonteCarloEventList()    
    event_list.set_column('TIME', col_time)    
    event_list.set_column('MC_ENERGY', col_mc_energy)
    col_pha = edisp.matrix.rvs(col_mc_energy)
    event_list.set_column('PHA', col_pha)
    col_energy = edisp.ebounds(col_pha)
    event_list.set_column('ENERGY',col_energy)
    event_list.set_column('MC_RA', col_mc_ra)
    event_list.set_column('MC_DEC', col_mc_dec)
    col_ra, col_dec = psf.smear(col_mc_ra, col_mc_dec)
    event_list.set_column('RA', col_ra)
    event_list.set_column('DEC', col_dec)
    pol_degree = polarization_degree(col_mc_energy, col_time, col_mc_ra,
                                                              col_mc_dec)
    pol_angle = polarization_angle(col_mc_energy, col_time, col_mc_ra,
                                                              col_mc_dec)
    col_pe_angle = modf.rvs_phi(col_mc_energy, pol_degree, pol_angle)
    event_list.set_column('PE_ANGLE', col_pe_angle)
    # Set the phase to rnd [0-1] for all non-periodic sources.
    phase=numpy.random.uniform(0,1,len(col_dec))
    event_list.set_column('PHASE', phase)   
    event_list.set_column('MC_SRC_ID', numpy.zeros(len(col_dec)))  
    logger.info('Done %s.' % chrono)
    
    simulation_info = xSimulationInfo()
    simulation_info.gti_list = gti_list
    simulation_info.roi_model = ROI_MODEL
    simulation_info.irf_name = kwargs['irfname']
    simulation_info.aeff = aeff
    simulation_info.psf = psf
    simulation_info.modf = modf
    simulation_info.edisp = edisp
    event_list.sort()
    event_list.write_fits(kwargs['outfile'], simulation_info)
    
    logger.info('All done %s!' % chrono)
    return kwargs['outfile']
    
if __name__=='__main__':
    args = PARSER.parse_args()
    startmsg()
    chandra2ximpol(args.evfile, **args.__dict__)
