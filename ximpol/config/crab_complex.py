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



#from ximpol.config.crab_nebula import ROI_MODEL as NEBULA_ROI_MODEL
from ximpol.config.crab_nebula_complex import ROI_MODEL as NEBULA_ROI_MODEL
from ximpol.config.crab_pulsar import ROI_MODEL as PULSAR_ROI_MODEL

ROI_MODEL = NEBULA_ROI_MODEL# + PULSAR_ROI_MODEL


if __name__ == '__main__':
    print(ROI_MODEL)
