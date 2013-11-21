__all__ = [
    "PrimaryElect",
]
import nparcel
from nparcel.utils.log import log


class PrimaryElect(nparcel.Service):
    """Nparcel PrimaryElect class.

    .. attribute:: parser

        :mod:`nparcel.StopParser` parser object

    .. attribute:: ts_db

        :mod:`cx_Oracle.Connection` object manager that interfaces
        to the TransSend database

    .. attribute:: delivered_header

        string that represents the TransSend column header name for
        a delivered item (default ``latest_scan_event_action``)

    .. attribute:: delivered_event_key

        string that represents a delivered event
        (default ``delivered``)

    """
    _parser = nparcel.StopParser()
    _ts_db = None
    _delivered_header = 'latest_scan_event_action'
    _delivered_event_key = 'delivered'

    def __init__(self, db=None, ts_db=None, comms_dir=None):
        """Nparcel PrimaryElect initialisation.

        """
        super(nparcel.PrimaryElect, self).__init__(db=db,
                                                   comms_dir=comms_dir)

        if ts_db is not None:
            self._ts_db = ts_db

    @property
    def parser(self):
        return self._parser

    @property
    def ts_db(self):
        return self._ts_db

    def set_ts_db(self, value):
        self._ts_db = value

    @property
    def delivered_header(self):
        return self._delivered_header

    @property
    def delivered_event_key(self):
        return self._delivered_event_key

    def get_primary_elect_job_item_id(self, connote):
        """Return ``jobitem.id`` whose connote is associated with a
        ``job`` that is defined *Primary Elect* (``job.service_code`` = 3).

        """
        ids = []
        sql = self.db.jobitem.connote_base_primary_elect_job(connote)
        self.db(sql)
        for row in self.db.rows():
            ids.append(row[0])

        return ids

    def get_uncollected_primary_elect_job_items(self):
        """Generator that returns the ``jobitem.id`` and
        ``jobitem.connote_nbr`` of uncollected Primary Elect job items.

        **Returns:**
            generator object which represents an uncollected job item
            in the form of a tuple data structure::

                (<jobitem.id>, <jobitem.connote_nbr>)

        """
        sql = self.db.jobitem.uncollected_primary_elect_jobitems_sql()
        self.db(sql)
        for row in self.db.rows():
            yield row

    def process(self, mts_file=None, dry=False):
        """Checks whether a Primary Elect job item has had comms sent.

        **Kwargs:**
            *mts_file*: path to the MTS delivery report file

            *dry*: only report, do not execute

        **Returns:**
            list of primary elect job_items for whom notifications were
            successfully processed.  Successful represents whether a comms
            for email *and* SMS was produced.

        """
        processed_ids = []

        if mts_file is not None:
            self.parser.set_in_file(mts_file)
            self.parser.read()

        for (id,
             connote,
             item_nbr) in self.get_uncollected_primary_elect_job_items():
            log.info('Processing PE id|connote|item: "%s|%s|%s ..."' %
                     (id, connote, item_nbr))

            delivered_status = False
            if (self.parser.connote_delivered(connote) or
                self.connote_delivered(connote, item_nbr)):
                delivered_status = True

            if delivered_status:
                log.info('Preparing comms flag for job_item.id: %d' % id)
                if not dry:
                    if (self.flag_comms('email', id, 'pe') and
                        self.flag_comms('sms', id, 'pe')):
                        processed_ids.append(id)
                else:
                    log.error('Comms flag error for job_item.id: %d' % id)

            log.info('PE id|connote|item: "%s|%s|%s" check complete' %
                     (id, connote, item_nbr))

        if mts_file is not None:
            self.parser.purge()

        return processed_ids

    def connote_delivered(self, connote_nbr, item_nbr):
        """Check if *connote_nbr* and *item_nbr* has been delivered.

        Uses the TransSend database as source.

        **Args:**
            *connote_nbr*: Connote value relating to the
            ``transsend.connote_number`` column

            *item_nbr*: Item number value relating to the
            ``transsend.item_number`` column

        **Returns:**
            boolean ``True`` if the *connote*/*item_nbr* combination
            has been delivered

        """
        log.info('TransSend checking connote|item "%s|%s" delivery status' %
                 (connote_nbr, item_nbr))

        delivered = False
        if self.ts_db is not None:
            sql = self.ts_db.transsend.connote_sql(connote_nbr=connote_nbr,
                                                   item_nbr=item_nbr)
            self.ts_db(sql)

            headers = self.ts_db.columns()
            index = headers.index(self.delivered_header)
            log.debug('Delivered header index: %d' % index)

            for row in self.ts_db.rows():
                log.debug('TransSend "%s" value: "%s"' %
                          (self.delivered_header, row[index].lower()))
                if row[index].lower() == self.delivered_event_key:
                    delivered = True
                    break

        log.info('TransSend connote|item "%s|%s" delivery status: %s' %
                 (connote_nbr, item_nbr, delivered))

        return delivered
