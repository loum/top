#!/usr/bin/python

import nparcel
from nparcel.utils.log import log


def main():
    """
    """
    loader = nparcel.Loader()

    file = 'T1250_TOLP_20130413135756.txt'

    log.info('Processing file: "%s" ...' % file)
    try:
        f = open(file, 'r')

        for line in f:
            record = line.rstrip('\r\n')
            if record == '%%EOF':
                log.info('EOF found')
            else:
                log.debug("processing line: %s" % record)
                try:
                    loader.process(record)
                except ValueError, e:
                    log.error('Error: "%s"' % e)

        f.close()
    except IOError, e:
        log.error('Error opening file "%s": %s' % (file, str(e)))

if __name__ == '__main__':
    main()
