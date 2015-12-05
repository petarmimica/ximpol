#!/usr/bin/env python
# *********************************************************************
# * Copyright (C) 2015 Luca Baldini (luca.baldini@pi.infn.it)         *
# *                                                                   *
# * For the license terms see the file LICENSE, distributed           *
# * along with this software.                                         *
# *********************************************************************
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


import glob
import os
import shutil
from ximpol.__logging__ import logger
from ximpol.__package__ import *


def cleanup(folderPath, patterns = ['*~', '*.pyc', '*.pyo']):
    """ Cleanup a folder.
    """
    logger.info('Cleaning up folder %s...' % folderPath)
    fileList = []
    for pattern in patterns:
        fileList += glob.glob(os.path.join(folderPath, pattern))
    for filePath in fileList:
        logger.info('Removing %s...' % filePath)
        os.remove(filePath)

def cleanupdist():
    """
    """
    if os.path.exists(XIMPOL_DIST):
        logger.info('Removing %s altogether...' % XIMPOL_DIST)
        shutil.rmtree(XIMPOL_DIST)
    filePath = os.path.join(XIMPOL_ROOT, 'MANIFEST')
    if os.path.exists(filePath):
        logger.info('Removing %s...' % filePath)
        os.remove(filePath)



if __name__ == '__main__':
    for folderPath in [XIMPOL_ROOT, XIMPOL_DIST, XIMPOL_DOC, XIMPOL_IRF,
                       XIMPOL_UTILS]:
        cleanup(folderPath)
    cleanupdist()