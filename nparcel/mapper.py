__all__ = [
    "Mapper",
]
import nparcel
from nparcel.utils.log import log

FIELDS = {'Conn Note': {'offset': 0,
                        'length': 20},
          'Identifier': {'offset': 22,
                         'length': 17},
          'System Identifier': {'offset': 29,
                                'length': 4},
          'ADP Type': {'offset': 39,
                       'length': 2},
          'Consumer Name': {'offset': 41,
                            'length': 40},
          'Consumer Address 1': {'offset': 81,
                                 'length': 30},
          'Consumer Address 2': {'offset': 111,
                                 'length': 30},
          'Suburb': {'offset': 141,
                     'length': 30},
          'Post code': {'offset': 171,
                        'length': 6},
          'Bar code': {'offset': 438,
                       'length': 15},
          'Pieces': {'offset': 588,
                     'length': 5},
          'Agent Id or Location Id': {'offset': 663,
                                      'length': 4},
          'Item Number': {'offset': 887,
                          'length': 32},
          'Mobile Number': {'offset': 925,
                            'length': 10},
          'Email Address': {'offset': 997,
                            'length': 60}}

MAP = {'Conn Note': {'offset': 0},
       'Identifier': {'offset': 22},
       'Consumer Name': {'offset': 41},
       'Consumer Address 1': {'offset': 81},
       'Consumer Address 2': {'offset': 111},
       'Suburb': {'offset': 141},
       'Post code': {'offset': 171},
       'Bar code': {'offset': 438},
       'Pieces': {'offset': 588},
       'Agent Id or Location Id': {'offset': 453},
       'Email Address': {'offset': 765},
       'Mobile Number': {'offset': 825},
       'Service Code': {'offset': 842},
       'Item Number': {'offset': 887}}


class Mapper(object):
    """Nparcel Mapper object.

    """
    _parser = nparcel.Parser(fields=FIELDS)

    def __init__(self):
        """Nparcel Mapper initialiser.

        """
        pass

    def translate(self, raw):
        """Translate source record into Nparcel T1250 format.

        **Args:**
            *raw*: the source record to translate

        **Returns:**
            ``None`` if the translation process fails

            string representation of a Nparcel T1250 record (1248 character
            length)

        """
        translated_line = None
        parsed_dict = self.parser.parse_line(raw)

        if (parsed_dict.get('ADP Type') is not None and
            parsed_dict.get('ADP Type') == 'PE'):
            log.info('Found PE flag')

            parsed_dict['Service Code'] = '3'

            translated_list = [' '] * 1248

            log.debug('length of initialised list: %d' % len(translated_list))

            for k, v in MAP.iteritems():
                log.info('Mapping field "%s" ...' % k)

                key_offset = v.get('offset')
                if key_offset is None:
                    log.warn('Mapping offset for key %s not defined' % k)
                    continue

                log.debug('Mapping offset for key %s: %s' % (k, key_offset))
                log.debug('Raw value is "%s"' % parsed_dict.get(k))

                index = 0
                for i in list(parsed_dict.get(k)):
                    translated_list[key_offset + index] = i
                    index += 1

            log.debug('length of xlated list: %d' % len(translated_list))
            translated_line = ''.join(translated_list)

        return translated_line

    @property
    def parser(self):
        return self._parser
