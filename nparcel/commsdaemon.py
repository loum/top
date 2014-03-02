__all__ = [
    "CommsDaemon",
]
import signal
import time
import datetime
import os
import re
import ConfigParser

import nparcel
from nparcel.utils.log import log


class CommsDaemon(nparcel.DaemonService):
    """Daemoniser facility for the :class:`nparcel.Comms` class.

    .. attribute:: comms_dir

         directory where comms files are read from for further processing

    .. attribute:: q_warning

        comms queue warning threshold.  If number of messages exceeds this
        threshold (and is under the :attr:`q_error` threshold then a
        warning email notification is triggered

    .. attribute:: q_error

        comms queue error threshold.  If number of messages exceeds this
        threshold then an error email notification is triggered and
        the comms daemon is terminated

    .. attribute:: skip_days (comms)

        list of days ['Saturday', 'Sunday'] to not send messages.  An empty
        list (or no skip days) suggests that comms can be sent on any day

    .. attribute:: send_time_ranges (comms)

        time ranges when comms can be sent.  An empty list (or no
        time ranges) suggests that comms can be sent at any time

    """
    _comms = None
    _comms_dir = None
    _q_warning = 100
    _q_error = 1000
    _skip_days = ['Sunday']
    _send_time_ranges = ['08:00-19:00']

    def __init__(self,
                 pidfile,
                 file=None,
                 dry=False,
                 batch=False,
                 config=None):
        self._facility = self.__class__.__name__
        super(CommsDaemon, self).__init__(pidfile=pidfile,
                                          file=file,
                                          dry=dry,
                                          batch=batch)

        if config is not None:
            self.config = nparcel.CommsB2CConfig(file=config)
            self.config.parse_config()

        try:
            self.set_support_emails(self.config.support_emails)
        except AttributeError, err:
            msg = ('%s support_emails not defined in config -- using %s' %
                   (self._facility, str(self.support_emails)))
            log.debug(msg)

        try:
            self.set_comms_dir(self.config.comms_dir)
        except AttributeError, err:
            msg = ('%s comms_dir not in config -- using %s' %
                   (self._facility, self.comms_dir))
            log.debug(msg)

        try:
            self.set_loop(self.config.comms_loop)
        except AttributeError, err:
            log.debug('%s comms_loop not in config -- using %d sec' %
                      (self._facility, self.loop))

        try:
            self.set_q_warning(self.config.comms_q_warning)
        except AttributeError, err:
            msg = ('%s q_warning not in config -- using %s' %
                   (self._facility, self.q_warning))
            log.debug(msg)

        try:
            self.set_q_error(self.config.comms_q_error)
        except AttributeError, err:
            msg = ('%s q_error not in config -- using %s' %
                   (self._facility, self.q_error))
            log.debug(msg)

        try:
            self.set_skip_days(self.config.skip_days)
        except AttributeError, err:
            log.debug('%s skip_days not in config -- using %s' %
                      (self._facility, self.skip_days))

        try:
            self.set_send_time_ranges(self.config.send_time_ranges)
        except AttributeError, err:
            log.debug('%s send_time_ranges not in config -- using %s' %
                      (self._facility, self.send_time_ranges))

    @property
    def comms(self):
        return self._comms

    @property
    def comms_dir(self):
        return self._comms_dir

    def set_comms_dir(self, value):
        self._comms_dir = value
        log.debug('%s comms_dir to "%s"' %
                  (self._facility, self.comms_dir))

    @property
    def q_warning(self):
        return self._q_warning

    def set_q_warning(self, value):
        self._q_warning = value

    @property
    def q_error(self):
        return self._q_error

    def set_q_error(self, value):
        self._q_error = value

    @property
    def skip_days(self):
        return self._skip_days

    def set_skip_days(self, values=None):
        del self._skip_days[:]
        self._skip_days = []

        if values is not None:
            self._skip_days.extend(values)
            log.debug('%s skip days set to "%s"' %
                      (self._facility, str(self.skip_days)))

    @property
    def send_time_ranges(self):
        return self._send_time_ranges

    def set_send_time_ranges(self, values=None):
        del self._send_time_ranges[:]
        self._send_time_ranges = []

        if values is not None:
            self._send_time_ranges.extend(values)
            log.debug('%s send_time_ranges set to "%s"' %
                      (self._facility, str(values)))

    @property
    def sms_api(self):
        sms_api = {}

        try:
            sms_api['api'] = self.config.get('rest', 'sms_api')
            sms_api['api_username'] = self.config.get('rest', 'sms_user')
            sms_api['api_password'] = self.config.get('rest', 'sms_pw')
            log.debug('%s SMS REST credentials: %s' %
                      (self._facility, str(sms_api)))
        except (ConfigParser.NoOptionError,
                ConfigParser.NoSectionError), err:
            log.debug('%s SMS REST credentials not in config: %s' %
                      (self._facility, err))

        return sms_api

    @property
    def email_api(self):
        email_api = {}

        try:
            email_api['api'] = self.config.get('rest', 'email_api')
            email_api['api_username'] = self.config.get('rest', 'email_user')
            email_api['api_password'] = self.config.get('rest', 'email_pw')
            email_api['support'] = self.config.get('rest', 'failed_email')
            log.debug('%s Email REST credentials: %s' %
                      (self._facility, str(email_api)))
        except (ConfigParser.NoOptionError,
                ConfigParser.NoSectionError), err:
            log.debug('%s Email REST credentials not in config: %s' %
                      (self._facility, err))

        return email_api

    @property
    def comms_kwargs(self):
        kwargs = {}
        try:
            kwargs['db'] = self.config.db_kwargs()
        except AttributeError, err:
            log.debug('%s TPP DB kwargs not in config: %s ' %
                      (self._facility, err))

        try:
            kwargs['proxy'] = self.config.proxy_string()
        except AttributeError, err:
            log.debug('%s proxy kwargs not in config: %s ' %
                      (self._facility, err))

        try:
            kwargs['scheme'] = self.config.proxy_scheme
        except AttributeError, err:
            log.debug('%s proxy scheme not in config: %s ' %
                      (self._facility, err))

        try:
            kwargs['sms_api'] = self.sms_api
        except AttributeError, err:
            log.debug('%s SMS REST credentials not in config: %s ' %
                      (self._facility, err))

        try:
            kwargs['email_api'] = self.email_api
        except AttributeError, err:
            log.debug('%s Email REST credentials not in config: %s ' %
                      (self._facility, err))

        return kwargs

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

        if self._comms is None:
            self._comms = nparcel.Comms(**(self.comms_kwargs))

        while not event.isSet():
            files = []

            if self._comms.db():
                if not self._skip_day():
                    if self._within_time_ranges():
                        if self.file is not None:
                            files.append(self.file)
                            event.set()
                        else:
                            files.extend(self.get_comms_files())
            else:
                log.error('ODBC connection failure -- aborting')
                event.set()
                continue

            # Start processing files.
            if self._message_queue_ok(len(files), dry=self.dry):
                for file in files:
                    self._comms.process(file, self.dry)
            else:
                log.info('Comms message queue threshold breached -- aborting')
                event.set()

            if not event.isSet():
                if self.dry:
                    log.info('Dry run iteration complete -- aborting')
                    event.set()
                elif self.batch:
                    log.info('Batch run iteration complete -- aborting')
                    event.set()
                else:
                    time.sleep(self.loop)

    def _skip_day(self):
        """Check whether comms is configured to skip current day of week.

        **Returns**:
            ``boolean``::

                ``True`` if current day is a skip day
                ``False`` if current day is **NOT** a skip day

        """
        is_skip_day = False

        current_day = datetime.datetime.now().strftime('%A').lower()
        log.debug('Current day/skip days: "%s/%s"' %
                  (current_day.title(), str(self.skip_days)))

        if current_day in [x.lower() for x in self.skip_days]:
            log.info('%s is a configured comms skip day' %
                     current_day.title())
            is_skip_day = True

        log.debug('Is a comms skip day?: "%s"' % str(is_skip_day))

        return is_skip_day

    def _within_time_ranges(self):
        """Check whether comms is configured to send comms at current time.

        Expects ranges to be of the format 'HH:MM-HH:MM' otherwise it will
        return ``False`` as no assumptions are made.

        **Returns**:
            ``boolean``::

            ``True`` if current time is within the ranges
            ``False`` if current day is **NOT** within the ranges

        """
        is_within_time_range = True

        current_time = datetime.datetime.now()
        log.debug('Current time/send_time_ranges: "%s/%s"' %
                  (str(current_time).split('.')[0],
                   str(self.send_time_ranges)))

        for range in self.send_time_ranges:
            try:
                (lower_str, upper_str) = range.split('-')
            except ValueError, err:
                log.error('Time range "%s" processing error: %s' %
                          (range, err))
                is_within_time_range = False
                break

            lower_str = '%s %s' % (current_time.strftime('%Y-%m-%d'),
                                   lower_str)
            log.debug('Lower date string: %s' % lower_str)
            upper_str = '%s %s' % (current_time.strftime('%Y-%m-%d'),
                                   upper_str)
            log.debug('Upper date string: %s' % upper_str)

            lower_time = time.strptime(lower_str, "%Y-%m-%d %H:%M")
            lower_dt = datetime.datetime.fromtimestamp(time.mktime(lower_time))
            upper_time = time.strptime(upper_str, "%Y-%m-%d %H:%M")
            upper_dt = datetime.datetime.fromtimestamp(time.mktime(upper_time))

            if current_time < lower_dt or current_time > upper_dt:
                is_within_time_range = False
                break

        log.debug('Is current time with range?: %s' %
                    str(is_within_time_range))

        return is_within_time_range

    def _message_queue_ok(self, message_count, dry=False):
        """Check if the *message_count* breaches the configured thresholds.

        Will send email to support if thresholds are breached.  Furthermore,
        if the higher threshold is breached, the comms facility will be
        terminated pending further investigation.

        **Args:**
            *message_count*: message queue length

        **Kwargs:**
            *dry*: only report, do not execute

        **Returns**:
            ``boolean``::

            ``True`` if queue lengths are within accepted thresholds
            ``False`` if queue lengths are NOT within accepted thresholds

        """
        queue_ok = True

        current_dt_str = datetime.datetime.now().strftime('%c')
        if message_count > self.q_error:
            log.info('Message queue count %d breaches error threshold %d' %
                     (message_count, self.q_error))
            queue_ok = False

            subject = ('Error - Nparcel Comms message count was at %d' %
                       message_count)
            d = {'count': message_count,
                 'date': current_dt_str,
                 'error_threshold': self.q_error}
            mime = self.emailer.create_comms(subject=subject,
                                             data=d,
                                             template='message_q_err')
            self.emailer.send(mime_message=mime, dry=dry)
        elif message_count > self.q_warning:
            log.info('Message queue count %d breaches warning threshold %d' %
                     (message_count, self.q_warning))

            subject = ('Warning - Nparcel Comms message count was at %d' %
                       message_count)
            d = {'count': message_count,
                 'date': current_dt_str,
                 'warning_threshold': self.q_warning}
            mime = self.emailer.create_comms(subject=subject,
                                             data=d,
                                             template='message_q_warn')
            self.emailer.send(mime_message=mime, dry=dry)

        return queue_ok

    def get_comms_files(self):
        """Produce a list of files in the :attr:`comms_dir`.

        Comms files are matched based on the following pattern::

            <action>.<job_item.id>.<template>

        where:

        * ``<action>`` is the communications medium (either SMS or email are
          supported)
          job_item table
        * ``<job_item.id>`` is the integer based primary key from the
          job_item table
        * ``<template>`` is the string template used to build the message
          content

        **Returns:**
            list of files to process or empty list if the :attr:`comms_dir`
            is not defined or does not exist

        """
        comms_files = []

        log.debug('Searching for comms in dir: %s' % self.comms_dir)

        if self.comms_dir is not None:
            if not os.path.exists(self.comms_dir):
                log.error('Comms directory "%s" does not exist' %
                          self.comms_dir)
            else:
                for f in os.listdir(self.comms_dir):
                    r = re.compile("^(email|sms)\.(\d+)\.(pe|rem|body|delay)$")
                    m = r.match(f)
                    if m:
                        comms_file = os.path.join(self.comms_dir, f)
                        log.info('Found comms file: "%s"' % comms_file)
                        comms_files.append(comms_file)
        else:
            log.error('Comms dir is not defined')

        return comms_files
