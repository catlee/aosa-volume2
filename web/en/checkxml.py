#!/usr/bin/env python

import sys
import re
import xml.etree.ElementTree as ET
from htmlentitydefs import entitydefs

#-------------------------------------------------------------------------------

entity_pat = re.compile(r'&(\w+);')

def replace(match):
    """
    Replace entity references with numerical codes.
    """
    escape = match.group(1)
    assert escape in entitydefs, 'Unknown escape character "%s"' % escape
    return entitydefs[escape][1:-1]

#-------------------------------------------------------------------------------

def readxml(filename):
    """
    Read in a document, returning the ElementTree doc node.
    """

    r = open(filename, 'r')
    data = r.read()
    r.close()
    data = entity_pat.sub(replace, data)
    try:
        return ET.fromstring(data)
    except ET.ParseError, e:
        print filename, e
        return None

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    for filename in sys.argv[1:]:
        readxml(filename)
