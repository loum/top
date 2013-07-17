__all__ = [
    "Loader",
]
import re
import datetime

import nparcel
from nparcel.utils.log import log

FIELDS = {'Conn Note': {'offset': 0,
                        'length': 20},
          'Identifier': {'offset': 21,
                         'length': 20},
          'Consumer Name': {'offset': 41,
                            'length': 30},
          'Consumer Address 1': {'offset': 81,
                                 'length': 30},
          'Consumer Address 2': {'offset': 111,
                                 'length': 30},
          'Suburb': {'offset': 141,
                     'length': 30},
          'Post code': {'offset': 171,
                        'length': 4},
          'state': {'offset': 171,
                    'length': 4},
          'Bar code': {'offset': 438,
                       'length': 15},
          'Agent Id': {'offset': 453,
                       'length': 4},
          'Pieces': {'offset': 588,
                     'length': 5}}
JOB_MAP = {'Agent Id': {
               'column': 'agent_id',
               'required': True,
               'callback': 'get_agent_id'},
           'Bar code': {
               'column': 'card_ref_nbr',
               'required': True},
           'Identifier': {
               'column': 'bu_id',
               'required': True,
               'callback': 'translate_bu_id'},
           'Consumer Address 1': {
               'column': 'address_1'},
           'Consumer Address 2': {
               'column': 'address_2'},
           'Suburb': {
               'column': 'suburb'},
           'Post code': {
               'column': 'postcode'},
           'state': {
               'column': 'state',
               'callback': 'translate_postcode'},
           'status': {
               'column': 'status',
               'required': True,
               'default': 1}}
JOB_ITEM_MAP = {'Conn Note': {
                    'column': 'connote_nbr'},
                'Consumer Name': {
                    'column': 'consumer_name'},
                'Pieces': {
                    'column': 'pieces'},
                'status': {
                    'column': 'status',
                    'required': True,
                    'default': 1},
                'created_ts': {
                    'column': 'created_ts',
                    'required': True,
                    'callback': 'date_now'}}
BU_MAP = {'TOLP': 1,
          'TOLF': 2,
          'TOLI': 3}
POSTCODE_MAP = {'NSW': {
                    'ranges': [
                        (1000, 1999),
                        (2000, 2599),
                        (2619, 2898),
                        (2921, 2999)],
                    'exceptions': [
                         2899]},
                'ACT': {
                    'ranges': [
                        (200, 299),
                        (2600, 2618),
                        (2900, 2920)],
                    'exceptions': []},
                'VIC': {
                    'ranges': [
                        (3000, 3999),
                        (8000, 8999)],
                    'exceptions': []},
                'QLD': {
                    'ranges': [
                        (4000, 4999),
                        (9000, 9999)],
                    'exceptions': []},
                'SA': {
                    'ranges': [],
                    'exceptions': []},
                'WA': {
                    'ranges': [
                        (5000, 5999)],
                    'exceptions': []},
                'TAS': {
                    'ranges': [
                        (7000, 7999)],
                    'exceptions': []},
                'NT': {
                    'ranges': [
                        (800, 999)],
                    'exceptions': []}}


class Loader(object):
    """Nparcel Loader object.
    """

    def __init__(self):
        """
        """
        self.parser = nparcel.Parser(fields=FIELDS)
        self.db = nparcel.DbSession()
        self.db.connect()
        self.alerts = []

    def process(self, raw_record):
        """
        Extracts, validates and inserts an Nparcel record.

        **Args:**
            raw_record: raw record directly from a T1250 file.
        """
        status = True

        fields = self.parser.parse_line(raw_record)
        barcode = fields.get('Bar code')

        try:
            log.info('Barcode "%s" processing ...' % barcode)
            job_data = self.table_column_map(fields, JOB_MAP)
            job_item_data = self.table_column_map(fields, JOB_ITEM_MAP)
            log.info('Barcode "%s" OK.' % barcode)
        except ValueError, e:
            status = False
            msg = 'Barcode "%s" error: %s' % (barcode, e)
            log.error(msg)
            self.set_alert(msg)

        if status:
            if self.barcode_exists(barcode=barcode):
                log.info('Updating Nparcel barcode "%s"' % barcode)
            else:
                log.info('Creating Nparcel barcode "%s"' % barcode)
                self.db.create(job_data, job_item_data)

        return status

    def barcode_exists(self, barcode):
        """
        """
        status = False

        log.info('Checking if barcode "%s" exists in system' % barcode)
        self.db(self.db._job.check_barcode(barcode=barcode))
        if self.db.row:
            status = True

        return status

    def get_agent_id(self, agent):
        """Helper method to verify if an Agent ID is defined.
        """
        log.info('Checking if Agent Id "%s" exists in system ...' % agent)
        self.db(self.db._agent.check_agent_id(agent_id=agent))

        agent_id_row_id = self.db.row
        if agent_id_row_id is not None:
            agent_id_row_id = agent_id_row_id[0]
            log.info('Agent Id "%s" found: %s' % (agent, agent_id_row_id))
        else:
            log.error('Agent Id "%s" does not exist' % agent)

            # For testing only, create the record.
            # First insert will fail the test -- subsequent checks should
            # be OK.  This will ensure we get a mix during testing.
            if self.db.host == 'localhost':
                log.debug('TEST: Creating Agent Id "%s" record ...' % agent)
                agent_fields = {'code': agent}
                sql = self.db._agent.insert_sql(agent_fields)
                # Just consume the new row id.
                id = self.db.insert(sql)

        return agent_id_row_id

#    def validate(self, fields):
#        """Perform some T1250 validations around:
#
#        Barcode and Agent ID should exist.
#
#        """
#        status = True
#
#        if not fields.get('Bar code'):
#            raise ValueError('Missing barcode')
#            status = False
#
#        if status and not fields.get('Agent Id'):
#            raise ValueError('Missing Agent Id')
#            status = False
#
#        return status

    def table_column_map(self, fields, map):
        """Convert the parser fields to Nparcel table column names in
        preparation for table manipulation.

        Runs a preliminary check to ensure that all items in *fields*
        can be mapped.  Raises a ``ValueError`` if otherwise.

        **Args:**
            fields: dictionary of :class:`nparcel.Parser` fields and
            values.

            map: dictionary of :class:`nparcel.Parser` fields to table
            columns.

        **Returns:**
            dictionary of table columns and values in the form::

                {'<column_1>': '<value>',
                 '<column_2>': '<value>'
                 ...}

        **Raises:**
            ValueError if all *fields* cannot be mapped.

        """
        columns = {}

        for field_name, v in map.iteritems():
            # Check for callbacks.
            if v.get('callback'):
                log.debug('Executing "%s" callback: "%s" ...' %
                          (field_name, v.get('callback')))
                callback = getattr(self, v.get('callback'))
                fields[field_name] = callback(fields.get(field_name))

            if (v.get('required') and
                not fields.get(field_name) and
                not v.get('default')):
                raise ValueError('Field "%s" is required' % field_name)

            if not fields.get(field_name):
                if v.get('default') is not None:
                    fields[field_name] = v.get('default')

        columns = dict((map.get(k).get('column'),
                        fields.get(k)) for (k, v) in map.iteritems())

        return columns

    def translate_bu_id(self, value):
        """
        """
        bu_id = None

        log.debug('Translating "%s" to BU ...' % value)
        m = re.search(' YMLML11(TOL.).*', value)
        bu_id = BU_MAP.get(m.group(1))

        if bu_id is None:
            log.error('Unable to extract BU from "%s"' % value)

        return bu_id

    def translate_postcode(self, postcode):
        """Translate postcode information to state.
        """
        log.debug('Translating postcode: "%s" ...' % str(postcode))
        state = ''

        if postcode:
            postcode = int(postcode)

            for postcode_state, postcode_ranges in POSTCODE_MAP.iteritems():
                for range in postcode_ranges.get('ranges'):
                    if postcode >= range[0] and postcode <= range[1]:
                        state = postcode_state
                        break
                for exception in  postcode_ranges.get('exceptions'):
                    if postcode == exception:
                        state = postcode_state
                        break

                if state:
                    break

        log.debug('Postcode "%s" translation produced: "%s"' %
                (str(postcode), state))

        return state

    def date_now(self, *args):
        """
        """
        return datetime.datetime.now().isoformat()

    def set_alert(self, alert):
        self.alerts.append(alert)

    def reset(self):
        """Reset the alert list.
        """
        del self.alerts[:]
