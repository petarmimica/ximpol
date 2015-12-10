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



import numbers

from ximpol.srcmodel.xModelElementBase import xModelElementBase



class xModelParameter(xModelElementBase):

    """ Small class representing a model parameter.
    """

    REQUIRED_KEYS = ['value']
    OPTIONAL_KEYS = ['unit']
    TYPE_DICT = {'value': numbers.Number}

    def __str__(self):
        """
        """
        _str = '%f' % self.value
        if self.name() is not None:
            _str = '%s = %s' % (self.name(), _str)
        if self.has_key('unit'):
            _str = '%s %s' % (_str, self.unit)
        return _str

    


def test():
    """ Test code.
    """
    from ximpol.srcmodel.xModelElementBase import ModelElementKeyMissing,\
        ModelElementKeyUnknown, ModelElementTypeError
    print(xModelParameter('p', value = 3))
    print(xModelParameter(value = 3))
    print(xModelParameter('p', value = 3, unit = 'keV'))
    try: 
        print(xModelParameter(value = '3'))
    except ModelElementTypeError as e:
        print(e)
    print(xModelParameter(value = 3, unit = 'keV'))
    try:
        print(xModelParameter())
    except ModelElementKeyMissing as e:
        print(e)
    try:
        print(xModelParameter(value = 3, test = False))
    except ModelElementKeyUnknown as e:
        print(e)



if __name__ == '__main__':
    test()
