__all__ = [
    "Config",
]
import os
import sys
import ConfigParser

from nparcel.utils.log import log

FLAG_MAP = {'item_number_excp': 0}


class Config(object):
    """Nparcel Config class.

    :class:`nparcel.Config` captures the configuration items required
    by the Nparcel B2C Replicator.

    .. attribute:: dirs_to_check (loader)

        list of directories to look for T1250 files.

    .. attribute:: archive (loader)

        directory to place processed T1250 files into.

    .. attribute:: staging_base (exporter)

        directory to place processed collected reports and signature files
        for further processing.

    .. attribute:: signature (exporter)

        directory where POD signature files are kept.

    .. attribute loader_loop (loader)

        time (seconds) between loader processing iterations.

    .. attribute:: exporter_loop (exporter)

        time (seconds) between exporter processing iterations.

    .. attribute:: business_units (exporter)

        the list of business units to query for collected items

    .. attribute:: cond (loader)

        dictionary of Business unit special condition flags

    """

    def __init__(self, file=None):
        """Nparcel Config initialisation.
        """

        self._file = file
        self._config = ConfigParser.SafeConfigParser()

        self.dirs_to_check = []
        self.archive = None
        self.signature = None
        self.loader_loop = 30
        self.exporter_loop = 900
        self.business_units = {}
        self.file_bu = {}
        self.support_emails = []
        self.special_emails = []
        self.special_sms = []
        self.cond = {}

        if self._file is not None:
            self.set_file(self._file)
            self.parse_config()

    def __call__(self, item=None):
        if item is None:
            return self._config

        value = None
        if item == 'in_dirs':
            value = self.dirs_to_check
        elif item == 'archive_dir':
            value = self.archive
        elif item == 'staging_base':
            value = self.staging_base
        elif item == 'signature_dir':
            value = self.signature
        elif item == 'loader_loop':
            value = self.loader_loop
        elif item == 'exporter_loop':
            value = self.exporter_loop
        elif item == 'business_units':
            value = self.business_units
        elif item == 'file_bu':
            value = self.file_bu
        elif item == 'support_emails':
            value = self.support_emails
        elif item == 'special_emails':
            value = self.special_emails
        elif item == 'special_sms':
            value = self.special_sms
        elif item == 'cond':
            value = self.cond

        return value

    def set_file(self, file):
        """
        """
        self._file = file

        if os.path.exists(self._file):
            log.debug('Parsing config file: "%s"' % file)
            self._config.read(file)
        else:
            log.critical('Unable to locate config file: "%s"' % file)
            sys.exit(1)

    def parse_config(self):
        """Read config items from the configuration file.

        """
        # Required items (fail if otherwise).
        if self._file is None:
            log.critical('Cannot parse config -- no file defined')
            sys.exit(1)

        try:
            self.dirs_to_check = self._config.get('dirs', 'in').split(',')
            log.debug('Loader directories to check %s' %
                      str(self.dirs_to_check))

            self.archive = self._config.get('dirs', 'archive')
            log.debug('Loader archive directory %s' % self.archive)

            self.staging_base = self._config.get('dirs', 'staging_base')
            log.debug('Exporter staging base %s' % self.staging_base)

            self.signature = self._config.get('dirs', 'signature')
            log.debug('Exporter signature directory %s' % self.signature)

            self.business_units = dict(self._config.items('business_units'))
            log.debug('Exporter Business Units %s' %
                      self.business_units.keys())

            self.file_bu = dict(self._config.items('file_bu'))
            log.debug('Exporter File Business Units %s' %
                      self.file_bu.keys())
        except ConfigParser.NoOptionError, err:
            log.critical('Missing required config: %s' % err)
            sys.exit(1)

        # Optional items (defaults provided).
        try:
            self.loader_loop = int(self._config.get('timeout',
                                                    'loader_loop'))
        except ConfigParser.NoOptionError, err:
            log.warn('Loader loop time not provided: %s' % err)
            pass

        try:
            self.exporter_loop = int(self._config.get('timeout',
                                                      'exporter_loop'))
        except ConfigParser.NoOptionError, err:
            log.warn('Exporter loop time not provided: %s' % err)
            pass

        try:
            self.support_emails = self._config.get('email',
                                                   'support').split(',')
        except ConfigParser.NoOptionError, err:
            log.warn('Support emails not provided: %s' % err)
            pass

        # Business unit condiitons.  No probs if they are missing -- will
        # just default to '0' (False) for each flag.
        try:
            self.cond = dict(self._config.items('conditions'))
            log.debug('Business Unit conditions %s' % self.cond.keys())
        except ConfigParser.NoSectionError, err:
            log.warn('Missing Business Unit conditions in config')

        try:
            self.special_emails = self._config.get('email',
                                                   'special').split(',')
        except ConfigParser.NoOptionError, err:
        #    log.warn('Special emails not provided: %s' % err)
            pass

        try:
            self.special_sms = self._config.get('sms',
                                                'special').split(',')
        except ConfigParser.NoOptionError, err:
        #    log.warn('Special SMSs not provided: %s' % err)
            pass

    def db_kwargs(self):
        """
        """
        kwargs = None

        # Base assumptions on "host" keyword.
        # No "host" means this must be a test scenario.
        try:
            host = self._config.get('db', 'host')
            driver = self._config.get('db', 'driver')
            database = self._config.get('db', 'database')
            user = self._config.get('db', 'user')
            password = self._config.get('db', 'password')
            port = self._config.get('db', 'port')
            kwargs = {'driver': driver,
                      'host': host,
                      'database': database,
                      'user': user,
                      'password': password,
                      'port': int(port)}
        except ConfigParser.NoOptionError, err:
            log.error('Missing DB key via config: %s' % err)

        return kwargs

    def condition(self, bu, flag):
        """Return the *bu* condition *flag* value.

        **Args:**
            bu: the name of the Business Unit.

            flag: name of the flag to process.

        **Returns:**
            boolean ``True`` if flag is '1'

            boolean ``False`` if flag is '0' or undefined

        """
        status = False

        if self.cond:
            index = FLAG_MAP.get(flag)
            if index is None:
                log.debug('Condition map undefined flag "%s"' % flag)
            else:
                if self.cond.get(bu) is None:
                    log.debug('Condition map missing BU "%s" option' % bu)
                else:
                    # Finally, get the flag!!!
                    try:
                        status = self.cond.get(bu)[index]
                        log.debug('Condition map %s:%s is "%s"' %
                                  (bu, flag, status))
                    except IndexError, e:
                        status = 0
        else:
            log.debug('Conditions config item is not defined')

        return status == '1'

    def condition_map(self, bu):
        """Return the *bu* condition map values.

        **Args:**
            bu: the name of the Business Unit.

        **Returns:**
            dict representing all of the condition flags for the *bu*

        """
        c_map = {}

        for flag in FLAG_MAP.keys():
            status = self.condition(bu, flag)
            log.debug('bu/flag - status | %s/%s - %s' % (bu, flag, status))
            c_map[flag] = status

        return c_map
