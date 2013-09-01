import unittest2
import datetime
import tempfile
import os

import nparcel

# Current business_unit map:
BU = {'ipec': 3}


class TestExporterIpec(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._seq = '0, 1, 2, 3, 4, 5, 6, 7'

        cls._e = nparcel.Exporter()

        # Prepare some sample data.
        # "agent" table.
        agents = [{'code': 'OK01'},
                  {'code': 'BAD1'}]
        agent_ok = cls._e.db.insert(cls._e.db._agent.insert_sql(agents[0]))
        agent_nok = cls._e.db.insert(cls._e.db._agent.insert_sql(agents[1]))

        cls._now = datetime.datetime.now()
        # "job" table.
        jobs = [{'card_ref_nbr': 'ipec card ref',
                 'agent_id': agent_ok,
                 'job_ts': '%s' % cls._now,
                 'bu_id': BU.get('ipec')}]
        sql = cls._e.db.job.insert_sql(jobs[0])
        cls._job_id = cls._e.db.insert(sql=sql)

        # "identity_type" table.
        identity_types = [{'description': 'License'},
                          {'description': 'Passport'}]
        sql = cls._e.db.identity_type.insert_sql(identity_types[0])
        cls._id_type_license = cls._e.db.insert(sql)
        sql = cls._e.db.identity_type.insert_sql(identity_types[1])
        cls._id_type_passport = cls._e.db.insert(sql)

        # "job_items" table.
        jobitems = [{'connote_nbr': 'ipec_connote_nbr_01',
                     'item_nbr': 'ipec_item_nbr_01',
                     'job_id': cls._job_id,
                     'pickup_ts': '%s' % cls._now,
                     'pod_name': 'pod_name ipec 01',
                     'identity_type_id': cls._id_type_license,
                     'identity_type_data': 'ipec identity 01'},
                    {'connote_nbr': 'ipec_connote_nbr_02',
                     'item_nbr': 'ipec_item_nbr_02',
                     'job_id': cls._job_id,
                     'pickup_ts': '%s' % cls._now,
                     'extract_ts': '%s' % cls._now,
                     'pod_name': 'pod_name ipec 02',
                     'identity_type_id': cls._id_type_passport,
                     'identity_type_data': 'ipec identity 02'}]

        for jobitem in jobitems:
            sql = cls._e.db.jobitem.insert_sql(jobitem)
            cls._e.db.insert(sql)

        cls._e.db.commit()

        # Create a temporary directory structure.
        cls._dir = tempfile.mkdtemp()
        cls._staging_dir = tempfile.mkdtemp()

    def test_header(self):
        """Ipec export file header generation.
        """
        sql = self._e.db.jobitem.collected_sql(business_unit=BU.get('ipec'))
        self._e.db(sql)

        # Get the query header.
        self._e.set_header(self._e.db.columns())

        received = self._e.get_report_line(line=self._e.header,
                                           sequence=self._seq)
        expected = ('%s|%s|%s|%s|%s|%s|%s|%s' % ('REF1',
                                                 'JOB_KEY',
                                                 'PICKUP_TIME',
                                                 'PICKUP_POD',
                                                 'IDENTITY_TYPE',
                                                 'IDENTITY_DATA',
                                                 'ITEM_NBR',
                                                 'AGENT'))
        msg = 'Ipec Exporter report header not as expected'
        self.assertEqual(received, expected, msg)

    def test_report_line_entry(self):
        """Ipec export file line entry generation.
        """
        sql = self._e.db.jobitem.collected_sql(business_unit=BU.get('ipec'))
        self._e.db(sql)

        # Extract report items from the DB.
        self._e.get_collected_items(business_unit_id=BU.get('ipec'))
        received = []
        for row in self._e._collected_items:
            received.append(self._e.get_report_line(line=row,
                                                    sequence=self._seq))
        expected = (['%s|%s|%s|%s|%s|%s|%s|%s' %
                    ('ipec_connote_nbr_01',
                     '1',
                     self._now.isoformat(' ')[:-7],
                     'pod_name ipec 01',
                     'License',
                     'ipec identity 01',
                     'ipec_item_nbr_01',
                     'OK01')])
        msg = 'Ipec Exporter report line items not as expected'
        self.assertListEqual(received, expected, msg)

    def test_process(self):
        """End to end collected items.
        """
        # Define the staging/signature directory.
        self._e.set_signature_dir(self._dir)
        self._e.set_staging_dir(self._staging_dir)

        # Prepare the signature files.
        bu = 'ipec'
        sql = self._e.db.jobitem.collected_sql(business_unit=BU.get(bu))
        self._e.db(sql)
        items = []
        for row in self._e.db.rows():
            items.append(row)
            fh = open(os.path.join(self._e.signature_dir,
                                   '%s.ps' % str(row[1])), 'w')
            fh.close()

        # Check if we can source a staging directory.
        out_dir = self._e.get_out_directory(business_unit=bu)
        valid_items = self._e.process(business_unit_id=BU.get('ipec'),
                                      out_dir=out_dir)
        sequence = '0, 1, 2, 3, 4, 5, 6, 7'
        report_file = self._e.report(valid_items,
                                     out_dir=out_dir,
                                     sequence=sequence)

        # Check the contents of the report file.
        fh = open(report_file)
        received = fh.read()
        fh.close()
        expected = ('%s|%s|%s|%s|%s|%s|%s|%s\n%s|%s|%s|%s|%s|%s|%s|%s\n' %
                    ('REF1',
                     'JOB_KEY',
                     'PICKUP_TIME',
                     'PICKUP_POD',
                     'IDENTITY_TYPE',
                     'IDENTITY_DATA',
                     'ITEM_NBR',
                     'AGENT',
                     'ipec_connote_nbr_01',
                     '1',
                     self._now.isoformat(' ')[:-7],
                     'pod_name ipec 01',
                     'License',
                     'ipec identity 01',
                     'ipec_item_nbr_01',
                     'OK01'))
        msg = 'Contents of Priority-based POD report file not as expected'
        self.assertEqual(received, expected, msg)

        # Clean.
        self._e.reset()
        os.remove(report_file)

        for item in items:
            # Remove the signature files.
            sig_file = os.path.join(self._e._staging_dir,
                                    'ipec',
                                    'out',
                                    '%s.ps' % str(item[1]))
            os.remove(sig_file)

            # Clear the extract_id timestamp.
            sql = """UPDATE job_item
SET extract_ts = null
WHERE id = %d""" % item[1]
            self._e.db(sql)

        os.rmdir(os.path.join(self._e.staging_dir, 'ipec', 'out'))
        os.rmdir(os.path.join(self._e.staging_dir, 'ipec'))
        self._e.set_staging_dir(value=None)
        self._e.set_signature_dir(value=None)

    @classmethod
    def tearDownClass(cls):
        cls._e = None
        os.removedirs(cls._dir)
        os.removedirs(cls._staging_dir)
        del cls._e
        del cls._dir
        del cls._staging_dir