__all__ = [
    "OnDeliveryDaemon",
]
import time
import signal
import re
import os

import nparcel
from nparcel.utils.log import log
from nparcel.utils.files import get_directory_files_list


class OnDeliveryDaemon(nparcel.DaemonService):
    """Daemoniser facility for the :class:`nparcel.OnDelivery` class.

    .. attribute:: report_in_dir

        TCD Delivery Report inbound directory
        (default ``/data/nparcel/tcd``)

    .. attribute:: report_file_format

        regular expression format string for inbound delivery report
        filename (default ``TCD_Deliveries_\d{14}\.DAT``)

    .. attribute:: comms_dir

        directory where comms files are kept for further processing

    .. attribute:: db_kwargs

        dictionary of connection string values for the Toll Parcel Point
        database.  Typical format is::

            {'driver': ...,
             'host': ...,
             'database': ...,
             'user': ...,
             'password': ...,
             'port': ...}

    .. attribute od

        :mod:`nparcel.OnDelivery` object

    .. attribute:: pe_bu_ids

        Business Unit IDs to use in the Primary Elect on delivery
        ``job_items`` table extraction

    .. attribute:: sc4_bu_ids

        Business Unit IDs to use in the Service Code 4 on delivery
        ``job_items`` table extraction

    .. attribute:: day_range

        Limit uncollected parcel search to within nominated day range
        (default 14.0 days)

    """
    _config = None
    _report_in_dirs = ['/data/nparcel/tcd']
    _report_file_format = 'TCD_Deliveries_\d{14}\.DAT'
    _comms_dir = '/data/nparcel/comms'
    _db_kwargs = None
    _od = None
    _pe_bu_ids = ()
    _sc4_bu_ids = ()
    _day_range = 14

    def __init__(self,
                 pidfile,
                 file=None,
                 dry=False,
                 batch=False,
                 config=None):
        super(OnDeliveryDaemon, self).__init__(pidfile=pidfile,
                                               file=file,
                                               dry=dry,
                                               batch=batch)

        if config is not None:
            self.config = nparcel.B2CConfig(file=config)
            self.config.parse_config()

        try:
            self.set_loop(self.config.ondelivery_loop)
        except AttributeError, err:
            log.debug('Daemon loop not in config -- default %d sec' %
                      self.loop)

        try:
            self.set_report_in_dirs(self.config.inbound_tcd)
        except AttributeError, err:
            msg = ('Report inbound dir not in config -- using %s' %
                   self.report_in_dirs)
            log.debug(msg)

        try:
            self.set_report_file_format(self.config.tcd_filename_format)
        except AttributeError, err:
            msg = ('Report file format not in config -- using %s' %
                   self.report_file_format)
            log.debug(msg)

        try:
            if self.config.comms_dir is not None:
                self.set_comms_dir(self.config.comms_dir)
        except AttributeError, err:
            msg = ('Comms dir not defined in config -- using %s' %
                   self.comms_dir)
            log.debug(msg)

        try:
            if self.config.db_kwargs() is not None:
                self.set_db_kwargs(self.config.db_kwargs())
        except AttributeError, err:
            log.debug('DB kwargs not defined in config')

        try:
            self.set_pe_bu_ids(self.config.pe_comms_ids)
        except AttributeError, err:
            msg = ('PE comms IDs not in config -- using %s' %
                   str(self.pe_bu_ids))
            log.debug(msg)

        try:
            self.set_sc4_bu_ids(self.config.sc4_comms_ids)
        except AttributeError, err:
            msg = ('SC 4 comms IDs not in config -- using %s' %
                   str(self.sc4_bu_ids))
            log.debug(msg)

        try:
            self.set_day_range(self.config.uncollected_day_range)
        except AttributeError, err:
            msg = ('Day range not in config -- using %s' %
                   str(self.day_range))
            log.debug(msg)

    @property
    def report_in_dirs(self):
        return self._report_in_dirs

    def set_report_in_dirs(self, values):
        del self._report_in_dirs[:]
        self._report_in_dirs = []

        if values is not None:
            log.debug('Setting inbound report directory to "%s"' % values)
            self._report_in_dirs.extend(values)

    @property
    def report_file_format(self):
        return self._report_file_format

    def set_report_file_format(self, value):
        log.debug('Setting report file format to "%s"' % value)
        self._report_file_format = value

    @property
    def comms_dir(self):
        return self._comms_dir

    def set_comms_dir(self, value):
        log.debug('Setting comms dir to "%s"' % value)
        self._comms_dir = value

    @property
    def db_kwargs(self):
        return self._db_kwargs

    def set_db_kwargs(self, value):
        if value is not None:
            self._db_kwargs = value

    @property
    def od(self):
        return self._od

    @property
    def pe_bu_ids(self):
        return self._pe_bu_ids

    def set_pe_bu_ids(self, values):
        self._pe_bu_ids = values

    @property
    def sc4_bu_ids(self):
        return self._sc4_bu_ids

    def set_sc4_bu_ids(self, values):
        self._sc4_bu_ids = values

    @property
    def day_range(self):
        return self._day_range

    def set_day_range(self, value):
        self._day_range = value

    def set_on_delivery(self, db=None, ts_db_kwargs=None, comms_dir=None):
        """Create a OnDelivery object,

        **Kwargs:**
            *db*: :mod:`nparcel.DbSession` object

            *ts_db_kwargs*: dictionary of key/value pairs representing
            the TransSend connection

            *comms_dir*: directory where to place comms events file
            for further processing

        """
        log.debug('Setting the OnDelivery object ...')
        if db is None:
            db = self.db_kwargs

        if ts_db_kwargs is None:
            try:
                ts_db_kwargs = self.config.ts_db_kwargs()
            except AttributeError, err:
                log.debug('TransSend DB kwargs not defined in config')

        if comms_dir is None:
            comms_dir = self.comms_dir

        if self._od is None:
            self._od = nparcel.OnDelivery(db_kwargs=db,
                                          ts_db_kwargs=ts_db_kwargs,
                                          comms_dir=comms_dir)

            try:
                self._od.set_delivered_header(self.config.delivered_header)
            except AttributeError, err:
                log.debug('Using default delivered_header: "%s"' %
                          self._od.delivered_header)

            try:
                event_key = self.config.delivered_event_key
                self._od.set_delivered_event_key(event_key)
            except AttributeError, err:
                log.debug('Using default delivered_event_key: "%s"' %
                          self._od.delivered_event_key)

            try:
                self._od.set_scan_desc_header(self.config.scan_desc_header)
            except AttributeError, err:
                log.debug('Using default scan_desc_header: "%s"' %
                          self._od.scan_desc_header)

            try:
                self._od.set_scan_desc_keys(self.config.scan_desc_keys)
            except AttributeError, err:
                log.debug('Using default scan_desc_keys: "%s"' %
                          self._od.scan_desc_keys)

    def _start(self, event):
        """Override the :method:`nparcel.utils.Daemon._start` method.

        Will perform a single iteration if the :attr:`file` attribute has
        a list of filenames to process.  Similarly, dry and batch modes
        only cycle through a single iteration.

        **Args:**
            *event* (:mod:`threading.Event`): Internal semaphore that
            can be set via the :mod:`signal.signal.SIGTERM` signal event
            to perform a function within the running proess.

        """
        signal.signal(signal.SIGTERM, self._exit_handler)

        self.set_on_delivery(comms_dir=self.comms_dir)

        while not event.isSet():
            tcd_files = []

            if not self.od.db() or not self.od.ts_db():
                log.error('ODBC connection failure -- aborting')
                event.set()
            else:
                if self.file is not None:
                    tcd_files.append(self.file)
                    event.set()
                else:
                    tcd_files.extend(self.get_files())

            tcd_file = None
            if len(tcd_files):
                tcd_file = tcd_files[0]

            log.debug('Attempting On Delivery Primary Elect check ...')
            if len(self.pe_bu_ids):
                processed_ids = self.od.process(template='pe',
                                                service_code=3,
                                                bu_ids=self.pe_bu_ids,
                                                tcd_file=tcd_file,
                                                day_range=self.day_range,
                                                dry=self.dry)
                log.debug('PE job_items.id comms files created: "%s"' %
                          processed_ids)
            else:
                log.debug("No Primary Elect BU ID's defined -- skipping")

            log.debug('Attempting Service Code 4 On Delivery check ...')
            if len(self.sc4_bu_ids):
                processed_ids = self.od.process(template='body',
                                                service_code=4,
                                                bu_ids=self.sc4_bu_ids,
                                                tcd_file=tcd_file,
                                                day_range=self.day_range,
                                                dry=self.dry)
                log.debug('SC 4 job_items.id comms files created: "%s"' %
                          processed_ids)
            else:
                log.debug("No Service Code 4 BU ID's defined -- skipping")

            if not event.isSet():
                if self.dry:
                    log.info('Dry run iteration complete -- aborting')
                    event.set()
                elif self.batch:
                    log.info('Batch run iteration complete -- aborting')
                    event.set()
                else:
                    time.sleep(self.loop)

    def validate_file(self, file):
        """Parse the TCD-format filename string confirm that it validates
        as per the accepted file name convention.

        Filename comparison is based on the ``pe_tcd_filename_format``
        config option.

        **Kwargs:**
            filename: the filename string to parse

        **Returns:**
            boolean ``True`` if the filename conforms th TCD report format
            boolean ``False`` otherwise

        """
        log.debug('Validating filename "%s" against "%s"' %
                  (file, self.report_file_format))
        status = False

        filename = os.path.basename(file)
        r = re.compile(self.report_file_format)
        m = r.match(filename)
        if m:
            status = True

        log.debug('"%s" filename validation: %s' % (file, status))

        return status

    def get_files(self):
        """Searches the :attr:`nparcel.OnDeliveryDaemon.report_in_dirs`
        configuration item as the source directory for TCD report files.

        There may be more than one TCD file available for processing
        but only the most recent instance will be returned.

        **Returns:**
            list if TCD delivery reports.  At this time, list will contain
            at most one TCD report file (or zero) if not matches are found.

        """
        report_files = []
        for report_in_dir in self.report_in_dirs:
            log.debug('Searching "%s" for report files' % report_in_dir)
            files = get_directory_files_list(report_in_dir,
                                             filter=self.report_file_format)

        for f in files:
            if self.validate_file(f):
                report_files.append(f)

        report_files.sort()
        log.debug('All report files: "%s"' % report_files)

        report_file = []
        if len(report_files):
            report_file.append(report_files[-1])
            log.debug('Using report file "%s"' % report_file)

        return report_file
