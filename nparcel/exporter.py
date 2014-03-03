__all__ = [
   "Exporter",
]
import re
import os
import datetime
import operator
import csv

import nparcel
from nparcel.utils.log import log
from nparcel.utils.files import (create_dir,
                                 remove_files,
                                 copy_file,
                                 get_directory_files_list,
                                 gen_digest_path)
from nparcel.timezone import convert_timezone

STATES = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'ACT']


class Exporter(nparcel.Service):
    """Nparcel Exporter.

    .. attribute:: archive_dir

        Where to archive signature files (if not being transfered).
        Default of ``None`` will not archive files

    .. attribute:: exporter_dirs

        Directory list for file-based events to trigger a ``job_item``
        closure

    .. attribute:: exporter_file_formats

        list of regular expressions that represent the type of files that
        can be parsed by the exporter

    .. attribute:: connote_header

        token used to identify the connote column in the Exporter report
        file

    .. attribute:: item_nbr_header

        token used to identify the item number column in the Exporter report
        file

    """
    _signature_dir = None
    _staging_dir = None
    _archive_dir = None
    _exporter_dirs = []
    _exporter_file_formats = []
    _connote_header = 'REF1'
    _item_nbr_header = 'ITEM_NBR'
    _time_fmt = "%Y-%m-%d %H:%M:%S"
    _time_tz_fmt = "%Y-%m-%d %H:%M:%S %Z%z"

    def __init__(self, **kwargs):
        """Exporter object initialiser.
        """
        super(nparcel.Exporter, self).__init__(db=kwargs.get('db'))

        self._signature_dir = kwargs.get('signature_dir')
        self._staging_dir = kwargs.get('staging_dir')
        create_dir(self._staging_dir)
        self._archive_dir = kwargs.get('archive_dir')
        create_dir(self._archive_dir)

        self._out_dir = None

        self._collected_items = []
        self._header = ()

        self.set_exporter_dirs(kwargs.get('exporter_dirs'))
        self.set_exporter_file_formats(kwargs.get('exporter_file_formats'))

        self.set_connote_header(kwargs.get('connote_header'))
        self.set_item_nbr_header(kwargs.get('item_nbr_header'))

    @property
    def signature_dir(self):
        return self._signature_dir

    def set_signature_dir(self, value):
        self._signature_dir = value

    @property
    def staging_dir(self):
        return self._staging_dir

    def set_staging_dir(self, value):
        self._staging_dir = value

        if self._staging_dir is not None:
            if not create_dir(self._staging_dir):
                self._staging_dir = None

    @property
    def out_dir(self):
        return self._out_dir

    def set_out_dir(self, business_unit):
        """Uses the *business_unit* name to construct the output directory
        to which the report and signature files will be placed for further
        processing.

        Staging directories are based on the Business Unit.  For example,
        the Business Unit "Priority" will create the directory
        ``priority/out`` off the base staging directory.

        Will check if the output directory structure exists before
        attempting to create it.

        **Args:**
            business_unit: name of the Business Unit that is associated
            with the collected items output files.

        """
        if business_unit is None:
            self._out_dir = None
        else:
            log.info('Checking output directory for "%s" ...' %
                     business_unit)
            try:
                self._out_dir = os.path.join(self.staging_dir,
                                             business_unit.lower(),
                                             'out')
                create_dir(self._out_dir)
            except AttributeError, err:
                log.error('Output directory error: "%s"' % err)
                self._out_dir = None

    @property
    def archive_dir(self):
        return self._archive_dir

    def set_archive_dir(self, value):
        self._archive_dir = value

        if self._archive_dir is not None:
            if not create_dir(self._archive_dir):
                self._archive_dir = None

    @property
    def exporter_dirs(self):
        return self._exporter_dirs

    def set_exporter_dirs(self, values):
        del self._exporter_dirs[:]
        self._exporter_dirs = []

        if values is not None:
            log.debug('Set exporter in directories "%s"' % str(values))
            self._exporter_dirs.extend(values)

    @property
    def exporter_file_formats(self):
        return self._exporter_file_formats

    def set_exporter_file_formats(self, values=None):
        del self._exporter_file_formats[:]
        self._exporter_file_formats = []

        if values is not None:
            self._exporter_file_formats.extend(values)
            log.debug('Set exporter file format list: "%s"' %
                      self.exporter_file_formats)

    @property
    def connote_header(self):
        return self._connote_header

    def set_connote_header(self, value=None):
        if value is not None:
            self._connote_header = value
            log.debug('Exporter set report file connote header to: "%s"' %
                      self.connote_header)

    @property
    def item_nbr_header(self):
        return self._item_nbr_header

    def set_item_nbr_header(self, value=None):
        if value is not None:
            self._item_nbr_header = value
            log.debug('Exporter set report file item nbr header to: "%s"' %
                      self.item_nbr_header)

    @property
    def header(self):
        return self._header

    def set_header(self, values):
        self._header = ()

        if values is not None:
            self._header = values

    @property
    def time_fmt(self):
        return self._time_fmt

    @property
    def time_tz_fmt(self):
        return self._time_tz_fmt

    def get_collected_items(self, business_unit_id, ignore_pe=False):
        """Query DB for recently collected items.

        **Args:**
            business_unit_id: business_unit.id

        """
        log.info('Searching for collected items ...')
        sql = self.db.jobitem.collected_sql(business_unit=business_unit_id)
        self.db(sql)

        # Get the query header.
        self.set_header(self.db.columns())

        for row in self.db.rows():
            cleansed_row = self._cleanse(row)
            self._collected_items.append(cleansed_row)

        log.info('Collected items: %d' % len(self._collected_items))

    def process(self,
                business_unit_id,
                file_control={'ps': True, 'png': False},
                archive_control={'ps': True, 'png': True},
                ignore_pe=False,
                dry=False):
        """
        Identifies picked up items and prepares reporting.  Sources both
        the database resource and file-based reports as input.

        Moves/archives signature files as defined by *file_control*.

        **Args:**
            business_unit_id: the Business Unit id as per "business_unit.id"
            column

        **Kwargs:**
            *file_control*: dictionary structure which controls whether the
            file extension type is moved or archived.  For example, the
            following structure sets '.ps' file extensions to be moved to
            the :attr:`out_dir` whilst ``*.png`` are moved to the
            :attr:`archive_dir`::

                {'ps': True,
                 'png': False}

            *dry*: only report what would happen (do not move file)

        """
        valid_items = []

        self.get_collected_items(business_unit_id, ignore_pe)

        for row in self._collected_items:
            job_item_id = row[1]

            # First, see if we need to archive the files.
            self.archive_signature_file(job_item_id,
                                        archive_control,
                                        self.signature_dir,
                                        self.archive_dir,
                                        dry=dry)

            # Check if file extension has been flagged to be
            # transferred out.  Finally, delete the file.
            for extension, send_to_out_dir in file_control.iteritems():
                sig_file = os.path.join(self.signature_dir,
                                        "%d.%s" % (job_item_id, extension))

                log.debug('Stage file "%s"?: %s' % (sig_file,
                                                    send_to_out_dir))
                status = os.path.exists(sig_file)
                if send_to_out_dir:
                    target = os.path.join(self.out_dir,
                                          os.path.basename(sig_file))
                    if not dry:
                        status = copy_file(sig_file, target)

                    # Only tag file sent to out_dir.
                    if status and row not in valid_items:
                        valid_items.append(row)

                # At this point, we can remove the file
                log.debug('Remove POD file "%s"?: %s' % (sig_file, status))
                if status and not dry:
                    remove_files(sig_file)

        return valid_items

    def archive_signature_file(self,
                               id,
                               archive_control,
                               in_dir,
                               out_dir,
                               dry=False):
        """Attempt to archive POD signature files.

        Archive directory name is constructed with the
        :func:`nparcel.utils.files.gen_digest_path` function.

        **Args:**
            *id*: the name of the POD signature file that relates to the
             ``job_item.id`` table column.

            *archive_control*: hash of file name extensions and boolean
            value to denote whether the file should be archived or not.
            Typical example is::

                {'ps': True,
                 'png': True}

            *in_dir*: directory that contains the source signature POD file

            *out_dir*: directory where signature POD files are archived to

        **Kwargs:**
            *dry*: only report what would happen (do not move file)

        **Returns:**
            boolean ``True`` if the *source_file* file is located
            and copied into *out_dir*

            boolean ``False`` otherwise

        """
        digest_path = gen_digest_path(str(id))
        target_dir = os.path.join(out_dir, *digest_path)

        for extension, archive in archive_control.iteritems():
            sig_file = "%d.%s" % (id, extension)
            sig_file_path = os.path.join(in_dir, sig_file)
            log.debug('Archiving "%s"?: %s' % (sig_file_path, archive))
            if archive and not dry:
                copy_file(sig_file_path, os.path.join(target_dir, sig_file))

    def _cleanse(self, row):
        """Runs over the "jobitem" record and modifies to suit the
        requirements of the report.

        **Args:**
            row: tuple representing the columns from the "jobitem" table
            record.

        **Returns:**
            tuple representing the cleansed data suitable for Nparcel
            exporter output.

        """
        log.debug('cleansing row: "%s"' % str(row))
        row_list = list(row)

        # "pickup_ts" column should have microseconds removed.
        # Handle sqlite and MSSQL dates differently.
        pickup_ts = row[2]
        if isinstance(row[2], str):
            m = re.match('(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d*',
                         row[2])
            try:
                pickup_ts = m.group(1)
            except AttributeError, err:
                log.error('Cannot cleanse pickup_ts "%s": %s' %
                          (row[2], err))
        elif isinstance(row[2], datetime.datetime):
            pickup_ts = row[2].strftime("%Y-%m-%d %H:%M:%S")
        log.debug('Cleansed pickup_ts: "%s"' % pickup_ts)
        row_list[2] = pickup_ts

        # Get rid of spaces around the state.
        try:
            row_list[8] = row_list[8].strip()
            log.debug('Cleansed state: "%s"' % row_list[8])
        except (IndexError, AttributeError), err:
            log.warn('Cleansed state -- no value: %s' % err)

        # Localise the time.
        row_list[2] = convert_timezone(row_list[2],
                                       row_list[8],
                                       self.time_fmt,
                                       self.time_tz_fmt)

        return tuple(row_list)

    def report(self,
               items,
               sequence=None,
               identifier='P',
               state_reporting=False,
               dry=False):
        """Cycle through the newly identified collected items and produce
        a report.

        Once an entry is made in the report, also update the database
        so that it does not appear in future runs.

        **Args:**
            items: list of report line item tuples

        **Kwargs:**
            sequence: business unit-based report column control

            identifier: business unit specific file identifier

            state_reporting: Business Unit reporting is output to separate
            files based on Agent state

        **Returns:**
            list of report file names that are generated

        """
        file_name = None

        target_files = []
        if not items:
            log.info('No collected items to report')
        else:
            index = self.get_header_column('JOB_KEY')
            sorted_items = sorted(items,
                                  key=operator.itemgetter(index),
                                  cmp=lambda x, y: int(x) - int(y))

            rpts = {}
            if state_reporting:
                log.debug('Reporting set to state based')
                state_col = self.get_header_column('AGENT_STATE')

                # Hardwired Fast fugliness.
                nt_rows = [r for r in sorted_items if r[state_col] == 'NT']
                tas_rows = [r for r in sorted_items if r[state_col] == 'TAS']

                for state in STATES:
                    log.debug('Reporting on state: %s' % state)
                    rows = [r for r in sorted_items if r[state_col] == state]

                    # Typical Fast fugliness, certain states tack onto
                    # others.
                    if state == 'VIC':
                        rows += tas_rows
                    if state == 'SA':
                        rows += nt_rows

                    log.debug('State row count: %d' % len(rows))
                    rpts[state] = {'id': identifier,
                                   'items': rows}
            else:
                # Just one report -- and it's the default name.
                rpts['VIC'] = {'id': identifier,
                               'items': sorted_items}

            for state, v in rpts.iteritems():
                if v.get('items') is not None and len(v.get('items')):
                    out_file = self.dump_report_output(v.get('items'),
                                                       sequence,
                                                       identifier,
                                                       state,
                                                       dry=dry)
                    if out_file is not None:
                        target_files.append(out_file)

        return target_files

    def dump_report_output(self,
                           sorted_items,
                           sequence,
                           identifier,
                           state='VIC',
                           dry=False):
        """
        Write out the contents contained within *sorted_items*.

        **Args:**
            sequence: business unit-based report column control

            identifier: business unit specific file identifier

        **Returns:**

            name of the report file produced (or ``None`` if no
            report was generated)

        """
        target_file = None

        header = self.get_report_line(self.header, sequence)
        if self.out_dir is None:
            print(header)
            for item in sorted_items:
                print('%s' % (self.get_report_line(item, sequence)))
        else:
            fh = self.outfile(self.out_dir, identifier, state)
            file_name = fh.name
            fh.write('%s\n' % header)
            for item in sorted_items:
                fh.write('%s\n' % self.get_report_line(item, sequence))
                job_item_id = item[1]
                self._update_status(job_item_id, dry=dry)
            fh.close()

            # Rename the output file so that it's ready for delivery.
            target_file = file_name.replace('.txt.tmp', '.txt')
            log.info('Renaming out file to "%s"' % target_file)
            os.rename(file_name, target_file)

        return target_file

    def get_report_line(self, line, sequence=None):
        """Generate the exporter report line entry.

        Provide a tuple *sequence* to control the items displayed and their
        order.

        **Args:**
            line: tuple of the collected item record as per the output from
            the job_item.collected_item() SQL

            sequence: tuple of values that represent the index of the
            fields that are returned by the job_item.collected_sql() query.
            For example:

                (0, 1, 4, 5, 2, 3)

        **Returns:**
            The exporter report header as a string if pipe delimited
            column names

        """
        report_line = "|".join(map(str, line))
        if sequence is None or not len(sequence):
            log.debug('Sequence not defined -- default line generated')
        else:
            seq = sequence
            if not isinstance(sequence, tuple):
                seq = (int(x) for x in sequence.replace(' ', '').split(','))

            try:
                report_line = "|".join(map(str, [line[i] for i in seq]))
            except IndexError, err:
                log.warn('Default report line entry generated: %s' % err)

        return report_line

    def outfile(self, dir, identifier, state='VIC'):
        """Creates the Exporter output file based on current timestamp
        and verifies creation at the staging directory *dir*.

        During output file access, prepends ``.tmp`` to the file.

        **Args:**
            dir: base directory name of the staging directory

            identifier: business unit specific file identifier

        **Returns:**
            open file handle to the exporter report file (or None if file
            access fails)

        """
        status = True
        fh = None

        create_dir(dir)

        if status:
            # Create the output file.
            time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            file = ("%s_%s_%s%s_%s.txt.tmp" %
                    (state, 'VANA', 'RE', identifier, time))
            file_path = os.path.join(dir, file)
            try:
                log.info('Opening file "%s"' % file_path)
                fh = open(file_path, 'wb')
            except IOError, err:
                status = False
                log.error('Could not open out file "%s": %s')

        return fh

    def _update_status(self, id, dry=False):
        """Set the job_item.extract_ts column of record *id* to the
        current date/time.

        **Args:**
            id: the job_item.id column value to update.

        """
        time = self.db.date_now()

        log.info('Updating extracted timestamp for job_item.id')
        sql = self.db.jobitem.upd_collected_sql(id, time)
        self.db(sql)
        if not dry:
            self.db.commit()

    def get_header_column(self, column_name):
        """Bit of a hard-wired fudge which just returns the list index
        of the *column_name* column.

        **Args:**
            column_name: name of column as per the exporter headers.  For
            example, 'JOB_KEY'

        **Returns:**
            integer value representing the index of the 'JOB_KEY' column
            or 0 if *column_name* column is not found

        """
        index = 0

        try:
            index = list(self.header).index(column_name)
        except ValueError, err:
            log.warn('"%s" not in exporter header' % column_name)

        return index

    def reset(self):
        """Initialise object state in readiness for another iteration.
        """
        self.set_alerts()

        del self._collected_items[:]
        self._header = ()
        self._out_dir = None

    def get_files(self, dirs=None, filters=None):
        """Checks inbound directories (defined by the
        :attr:`nparcel.b2cconfig.exporter_in` config option) or
        overridden by *dir* for files filtered against
        :attr:`nparcel.b2cconfig.exporter_file_formats` or overridden by
        *filters*.

        **Kwargs:**
            *dirs*: list of directories to search (override the value
            defined by :attr:`nparcel.b2cconfig.exporter_in`)

            *filters*: list of file filters (override the value defined
            by :attr:`nparcel.b2cconfig.exporter_file_formats`.

        **Returns:**
            list of filtered files

        """
        files = []

        dirs_to_check = []
        if dirs is not None:
            dirs_to_check.extend(dirs)
        else:
            dirs_to_check.extend(self.exporter_dirs)

        filters_to_use = []
        if filters is not None:
            filters_to_use.extend(filters)
        else:
            filters_to_use.extend(self.exporter_file_formats)

        log.debug('Searching report directories: "%s"' % str(dirs_to_check))
        for dir in dirs_to_check:
            for filter in filters_to_use:
                files.extend(get_directory_files_list(dir, filter))

        log.debug('Found report files: "%s"' % str(files))
        return files

    def parse_report_file(self, file):
        """Parse the contents of a report file and extract the connote
        and item number fields.

        **Args:**
            *file*: the absolute path to the report file to parse.

        **Returns**:

            tuple structure in the form (<connote>, <item_number>).  If
            either connote and item number is not defined then field
            is substituted with ``None``
        """
        values = []

        fh = None
        try:
            fh = open(file, 'r')
            log.info('Opened report file "%s" for reading ...' % file)
        except IOError, err:
            log.error('Unable to open report file: "%s"' % file)

        if fh is not None:
            reader = csv.DictReader(fh, delimiter='|')

            for rowdict in reader:
                connote = rowdict.get(self.connote_header)
                if connote is None:
                    # We need this because ParcelPoint return the 'REF1'
                    # column as 'Ref1' (just to be different ...)
                    title = self.connote_header.lower().title()
                    log.debug('Trying connote lookup as per title: "%s"' %
                              title)
                    connote = rowdict.get(title)
                item_nbr = rowdict.get(self.item_nbr_header)
                row = (connote, item_nbr)
                values.append(row)
                log.info('Parsed (connote|item_nbr): %s' % str(row))

        return values

    def file_based_updates(self, dry=False):
        """Close off records based on file input.

        **Kwargs:**
            *dry*: only report, do not execute.
        """
        for file in self.get_files():
            records = []
            records.extend(self.parse_report_file(file))

            for r in records:
                log.info('Closing off (connote|item_nbr): %s' % str(r))

                # Check that the record exists in the table.
                sql = self.db.jobitem.connote_item_nbr_sql(*r)
                self.db(sql)
                rows = list(self.db.rows())
                if not len(rows):
                    err_file = os.path.basename(file)
                    err = ('File-based record closure in file "%s"' %
                           err_file)
                    err = ('%s: %s no records found' % (err, str(r)))
                    self.set_alerts(err)
                    continue

                sql = self.db.jobitem.upd_file_based_collected_sql(*r)
                self.db(sql)
                if not dry:
                    self.db.commit()

            log.info('Deleting file: "%s"' % file)
            if not dry:
                remove_files(file)
