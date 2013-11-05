__all__ = [
    "PrimaryElectDaemon",
]
import time
import signal
import re
import os

import nparcel
from nparcel.utils.log import log
from nparcel.utils.files import get_directory_files_list


class PrimaryElectDaemon(nparcel.DaemonService):
    """Daemoniser facility for the :class:`nparcel.PrimaryElect` class.

    .. attribute:: report_in_dir

        MTS Delivery Report inbound directory
        (default ``/data/nparcel/mts``)

    .. attribute:: report_file_format

        regular expression format string for inbound delivery report
        filename (default ``mts_delivery_report_\d{14}\.csv``)

    .. attribute:: comms_dir

        directory where comms files are kept for further processing

    """
    _config = None
    _report_in_dirs = ['/data/nparcel/mts']
    _report_file_format = 'mts_delivery_report_\d{14}\.csv'
    _comms_dir = '/data/nparcel/comms'
    _db_kwargs = None
    _pe = None

    def __init__(self,
                 pidfile,
                 file=None,
                 dry=False,
                 batch=False,
                 config=None):
        super(PrimaryElectDaemon, self).__init__(pidfile=pidfile,
                                                 file=file,
                                                 dry=dry,
                                                 batch=batch)

        if config is not None:
            self.config = nparcel.B2CConfig(file=config)
            self.config.parse_config()

        try:
            self.set_loop(self.config.loader_loop)
        except AttributeError, err:
            log.info('Daemon loop not defined in config -- default %d sec' %
                     self.loop)

        try:
            self.set_in_dirs(self.config.pe_in_dir)
        except AttributeError, err:
            msg = ('Inbound directory not defined in config -- using %s' %
                   self.in_dirs)
            log.info(msg)

        try:
            self.set_report_in_dirs(self.config.pe_inbound_mts)
        except AttributeError, err:
            msg = ('Report inbound dir not defined in config -- using %s' %
                   self.report_in_dirs)
            log.info(msg)

        try:
            self.set_report_file_format(self.config.pe_mts_filename_format)
        except AttributeError, err:
            msg = ('Report file format not defined in config -- using %s' %
                   self.report_file_format)
            log.info(msg)

        try:
            if self.config.comms_dir is not None:
                self.set_comms_dir(self.config.comms_dir)
        except AttributeError, err:
            msg = ('Comms dir not defined in config -- using %s' %
                   self.comms_dir)
            log.info(msg)

        try:
            if self.config.db_kwargs() is not None:
                self.set_db_kwargs(self.config.db_kwargs())
        except AttributeError, err:
            msg = ('DB kwargs not defined in config')
            log.info(msg)

    @property
    def report_in_dirs(self):
        return self._report_in_dirs

    def set_report_in_dirs(self, values):
        del self._report_in_dirs[:]
        self._report_in_dirs = []

        if values is not None:
            log.info('Setting inbound report directory to "%s"' % values)
            self._report_in_dirs.extend(values)

    @property
    def report_file_format(self):
        return self._report_file_format

    def set_report_file_format(self, value):
        log.info('Setting report file format to "%s"' % value)
        self._report_file_format = value

    @property
    def comms_dir(self):
        return self._comms_dir

    def set_comms_dir(self, value):
        log.info('Setting comms dir to "%s"' % value)
        self._comms_dir = value

    @property
    def db_kwargs(self):
        return self._db_kwargs

    def set_db_kwargs(self, value):
        if value is not None:
            self._db_kwargs = value

    @property
    def pe(self):
        return self._pe

    def set_pe(self, db=None, comms_dir=None):
        if db is None:
            db = self.db_kwargs

        if comms_dir is None:
            comms_dir = self.comms_dir

        if self._pe is None:
            self._pe = nparcel.PrimaryElect(db=db, comms_dir=comms_dir)

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

        self.set_pe(comms_dir=self.comms_dir)

        while not event.isSet():
            files = []

            if self.pe.db():
                if self.file is not None:
                    files.append(self.file)
                    event.set()
                else:
                    files.extend(self.get_files())
            else:
                log.error('ODBC connection failure -- aborting')
                event.set()
                continue

            # Start processing files.
            for file in files:
                log.info('Processing file: "%s" ...' % file)
                if self.validate_file(file):
                    self.pe.process(file, dry=self.dry)

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
        """Parse the MTS-format filename string confirm that it validates
        as per the accepted file name convention.

        Filename comparison is based on the ``pe_mts_filename_format``
        config option.

        **Kwargs:**
            filename: the filename string to parse

        **Returns:**
            boolean ``True`` if the filename conforms th MTS report format
            boolean ``False`` otherwise

        """
        log.info('Validating filename "%s" against "%s"' %
                 (file, self.report_file_format))
        status = False

        filename = os.path.basename(file)
        r = re.compile(self.report_file_format)
        m = r.match(filename)
        if m:
            status = True

        log.info('"%s" filename validation: %s' % (file, status))

        return status

    def get_files(self):
        """Searches the :attr:`nparcel.PrimaryElectDaemon.report_in_dirs`
        configuration item as the source directory for MTS report files.

        There may be more than one MTS file available for processing
        but only the most recent instance will be returned.

        **Returns:**
            list if MTS delivery reports.  At this time, list will contain
            at most one MTS report file (or zero) if not matches are found.

        """
        report_files = []
        for report_in_dir in self.report_in_dirs:
            log.info('Searching "%s" for report files' % report_in_dir)
            files = get_directory_files_list(report_in_dir,
                                             filter=self.report_file_format)
            if len(files):
                report_files.extend(files)

        report_files.sort()
        log.debug('All report files: "%s"' % report_files)

        report_file = []
        if len(report_files):
            report_file.append(report_files[-1])
            log.info('Found report file "%s"' % report_file)

        return report_file
