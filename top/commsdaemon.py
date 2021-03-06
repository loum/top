__all__ = [
    "CommsDaemon",
]
import signal
import time
import datetime
import ConfigParser

import top
from top.utils.log import log
from top.utils.files import get_directory_files_list
from top.utils.setter import (set_scalar,
                              set_list)


class CommsDaemon(top.DaemonService):
    """Daemoniser facility for the :class:`top.Comms` class.

    .. attribute:: *comms_dir*

         directory where comms files are read from for further processing

    .. attribute:: *q_warning*

        comms queue warning threshold.  If number of messages exceeds this
        threshold (and is under the :attr:`q_error` threshold then a
        warning email notification is triggered

    .. attribute:: *q_error*

        comms queue error threshold.  If number of messages exceeds this
        threshold then an error email notification is triggered and
        the comms daemon is terminated

    .. attribute:: *controlled_templates*

        list of comms templates that are controlled by the delivery
        period thresholds

    .. attribute:: *uncontrolled_templates*

        list of comms templates that are *NOT* controlled by the delivery
        period thresholds.  In other words, comms can be sent 24 x 7

    .. attribute:: *skip_days*

        list of days ['Saturday', 'Sunday'] to not send messages.  An empty
        list (or no skip days) suggests that comms can be sent on any day

    .. attribute:: *send_time_ranges*

        time ranges when comms can be sent.  An empty list (or no
        time ranges) suggests that comms can be sent at any time

    """
    _comms = None
    _comms_dir = None
    _q_warning = 100
    _q_error = 1000
    _controlled_templates = ['body']
    _uncontrolled_templates = ['ret']
    _skip_days = ['Sunday']
    _send_time_ranges = ['08:00-19:00']

    @property
    def comms(self):
        return self._comms

    @property
    def comms_dir(self):
        return self._comms_dir

    @set_scalar
    def set_comms_dir(self, value):
        pass

    @property
    def q_warning(self):
        return self._q_warning

    @set_scalar
    def set_q_warning(self, value):
        pass

    @property
    def q_error(self):
        return self._q_error

    @set_scalar
    def set_q_error(self, value):
        pass

    @property
    def controlled_templates(self):
        return self._controlled_templates

    @set_list
    def set_controlled_templates(self, values=None):
        pass

    @property
    def uncontrolled_templates(self):
        return self._uncontrolled_templates

    @set_list
    def set_uncontrolled_templates(self, values=None):
        pass

    @property
    def skip_days(self):
        return self._skip_days

    @set_list
    def set_skip_days(self, values=None):
        pass

    @property
    def send_time_ranges(self):
        return self._send_time_ranges

    @set_list
    def set_send_time_ranges(self, values=None):
        pass

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
            kwargs['prod'] = self.prod
        except AttributeError, err:
            log.debug('%s prod instance name not in config: %s ' %
                      (self._facility, err))

        try:
            kwargs['db'] = self.config.db_kwargs()
        except AttributeError, err:
            log.debug('%s DB kwargs not in config: %s ' %
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

        try:
            kwargs['templates'] = (self.config.controlled_templates +
                                   self.config.uncontrolled_templates)
        except (ConfigParser.NoOptionError,
                ConfigParser.NoSectionError), err:
            log.debug('%s templates cannot be built from %s: %s ' %
                      (self._facility, 'comms.*controlled_templates', err))

        try:
            kwargs['returns_templates'] = self.config.uncontrolled_templates
        except (ConfigParser.NoOptionError,
                ConfigParser.NoSectionError), err:
            log.debug('%s returns_templates cannot be built from %s: %s ' %
                      (self._facility, 'comms.uncontrolled_templates', err))

        log.debug('%s comms_kwargs: "%s"' % (self.facility, kwargs))
        return kwargs

    def __init__(self,
                 pidfile,
                 file=None,
                 dry=False,
                 batch=False,
                 config=None):
        top.DaemonService.__init__(self,
                                   pidfile=pidfile,
                                   file=file,
                                   dry=dry,
                                   batch=batch,
                                   config=config)
        if self.config is not None:
            self.set_comms_dir(self.config.comms_dir)
            self.set_loop(self.config.comms_loop)
            self.set_q_warning(self.config.comms_q_warning)
            self.set_q_error(self.config.comms_q_error)
            self.set_controlled_templates(self.config.controlled_templates)
            tmp = self.config.uncontrolled_templates
            self.set_uncontrolled_templates(tmp)
            self.set_skip_days(self.config.skip_days)
            self.set_send_time_ranges(self.config.send_time_ranges)

    def _start(self, event):
        """Override the :method:`top.utils.Daemon._start` method.

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
            self._comms = top.Comms(**(self.comms_kwargs))

        all_templates = (self.controlled_templates +
                         self.uncontrolled_templates)
        log.info('Enabled templates: %s' % all_templates)

        while not event.isSet():
            files = []

            if not self._comms.db():
                log.error('ODBC connection failure -- aborting')
                event.set()
                continue

            if not self._skip_day():
                if self._within_time_ranges():
                    if self.file is not None:
                        files.append(self.file)
                        event.set()
                    else:
                        for filter in self.controlled_templates:
                            log.debug('controlled template filter: %s' %
                                      filter)
                            files.extend(self.get_comms_files(filter))

            for filter in self.uncontrolled_templates:
                log.debug('uncontrolled template filter: %s' % filter)
                files.extend(self.get_comms_files(filter))

            if len(files):
                self.reporter.reset('Comms')
                log.info('All files: "%s"' % files)

            # Start processing files.
            if self._message_queue_ok(len(files), dry=self.dry):
                for file in files:
                    self.reporter(self._comms.process(file, self.dry))

                if len(files):
                    stats = self.reporter.report()
                    log.info(stats)
            else:
                log.info('Comms queue threshold breached -- aborting')
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

        log.debug('Is current time within range?: %s' %
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

            subject = ('Error - Comms message count was at %d' %
                       message_count)
            d = {'count': message_count,
                 'date': current_dt_str,
                 'error_threshold': self.q_error}
            mime = self.emailer.create_comms(subject=subject,
                                             data=d,
                                             template='message_q_err',
                                             prod=self.prod)
            self._emailer.set_recipients(self.support_emails)
            self.emailer.send(mime_message=mime, dry=dry)
        elif message_count > self.q_warning:
            log.info('Comms queue count %d breaches warning threshold %d' %
                     (message_count, self.q_warning))

            subject = ('Warning - Comms message count was at %d' %
                       message_count)
            d = {'count': message_count,
                 'date': current_dt_str,
                 'warning_threshold': self.q_warning}
            mime = self.emailer.create_comms(subject=subject,
                                             data=d,
                                             template='message_q_warn',
                                             prod=self.prod)
            self._emailer.set_recipients(self.support_emails)
            self.emailer.send(mime_message=mime, dry=dry)

        return queue_ok

    def get_comms_files(self, template=None):
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

        **Kwargs:**
            *template*: template token to filter comms event files against

        **Returns:**
            list of files to process or empty list if the :attr:`comms_dir`
            is not defined or does not exist

        """
        log.debug('Searching for comms in dir: %s' % self.comms_dir)

        comms_files = []
        filter = '^(email|sms)\.(\d+)\.(\w+)$'
        if template is not None:
            filter = '^(email|sms)\.(\d+)\.(%s)$' % template
        comms_files.extend(get_directory_files_list(self.comms_dir,
                                                    filter))

        log.debug('Comms event files found: "%s"' % comms_files)

        return comms_files
