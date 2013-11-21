import unittest2
import datetime
import tempfile
import os

import nparcel
from nparcel.utils.files import remove_files


class TestPrimaryElect(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._comms_dir = tempfile.mkdtemp()
        cls._pe = nparcel.PrimaryElect(comms_dir=cls._comms_dir)
        test_dir = 'nparcel/tests/files'
        test_file = 'mts_delivery_report_20131018100758.csv'
        cls._test_file = os.path.join(test_dir, test_file)

        agents = [{'code': 'N031',
                   'state': 'VIC',
                   'name': 'N031 Name',
                   'address': 'N031 Address',
                   'postcode': '1234',
                   'suburb': 'N031 Suburb'},
                  {'code': 'BAD1',
                   'state': 'NSW',
                   'name': 'BAD1 Name',
                   'address': 'BAD1 Address',
                   'postcode': '5678',
                   'suburb': 'BAD1 Suburb'}]
        sql = cls._pe.db._agent.insert_sql(agents[0])
        agent_01 = cls._pe.db.insert(sql)
        sql = cls._pe.db._agent.insert_sql(agents[1])
        agent_02 = cls._pe.db.insert(sql)

        cls._now = datetime.datetime.now()
        jobs = [{'agent_id': agent_01,
                 'job_ts': '%s' % cls._now,
                 'bu_id': 1},
                {'agent_id': agent_01,
                 'job_ts': '%s' % cls._now,
                 'service_code': 3,
                 'bu_id': 1}]
        sql = cls._pe.db.job.insert_sql(jobs[0])
        job_01 = cls._pe.db.insert(sql)
        sql = cls._pe.db.job.insert_sql(jobs[1])
        job_02 = cls._pe.db.insert(sql)

        # Rules as follows:
        # id_000 - not primary elect
        # id_001 - primary elect with valid recipients/delivered
        # id_002 - primary elect no recipients
        # id_003 - primary elect/not delivered
        jobitems = [{'connote_nbr': 'con_001',
                     'item_nbr': 'item_nbr_001',
                     'email_addr': 'loumar@tollgroup.com',
                     'phone_nbr': '0431602145',
                     'job_id': job_01,
                     'created_ts': '%s' % cls._now},
                    {'connote_nbr': 'GOLW010997',
                     'item_nbr': 'item_nbr_002',
                     'email_addr': 'loumar@tollgroup.com',
                     'phone_nbr': '0431602145',
                     'job_id': job_02,
                     'created_ts': '%s' % cls._now},
                    {'connote_nbr': 'con_003',
                     'item_nbr': 'item_nbr_003',
                     'email_addr': '',
                     'phone_nbr': '',
                     'job_id': job_02,
                     'created_ts': '%s' % cls._now,
                     'pickup_ts': '%s' % cls._now},
                    {'connote_nbr': 'GOLW013730',
                     'item_nbr': 'item_nbr_004',
                     'email_addr': 'loumar@tollgroup.com',
                     'phone_nbr': '0431602145',
                     'job_id': job_02,
                     'created_ts': '%s' % cls._now}]
        sql = cls._pe.db.jobitem.insert_sql(jobitems[0])
        cls._id_000 = cls._pe.db.insert(sql)
        sql = cls._pe.db.jobitem.insert_sql(jobitems[1])
        cls._id_001 = cls._pe.db.insert(sql)
        sql = cls._pe.db.jobitem.insert_sql(jobitems[2])
        cls._id_002 = cls._pe.db.insert(sql)
        sql = cls._pe.db.jobitem.insert_sql(jobitems[3])
        cls._id_003 = cls._pe.db.insert(sql)

    def test_init(self):
        """Initialise a PrimaryElect object.
        """
        msg = 'Object is not a nparcel.PrimaryElect'
        self.assertIsInstance(self._pe, nparcel.PrimaryElect, msg)

    def test_get_primary_elect_job_item_id_not_pe(self):
        """jobitem.id's of connote that is not a primary elect job.
        """
        received = self._pe.get_primary_elect_job_item_id('con_001')
        expected = []
        msg = 'Non-primary elect job should produce empty list'
        self.assertListEqual(received, expected, msg)

    def test_get_primary_elect_job_item_id_valid_pe(self):
        """jobitem.id's of connote that is a primary elect job.
        """
        received = self._pe.get_primary_elect_job_item_id('GOLW010997')
        expected = [self._id_001]
        msg = 'Primary elect job should produce ids'
        self.assertListEqual(received, expected, msg)

    def test_get_primary_elect_job_item_id_valid_pe_no_comms(self):
        """jobitem.id's of connote that is a primary elect job -- no comms.
        """
        received = self._pe.get_primary_elect_job_item_id('con_003')
        expected = []
        msg = 'Primary elect job no recipients should produce empty list'
        self.assertListEqual(received, expected, msg)

    def test_process(self):
        """Check processing.
        """
        dry = True
        received = self._pe.process(self._test_file, dry=dry)
        expected = [self._id_001]
        msg = 'List of processed primary elect items incorrect'
        self.assertListEqual(received, expected, msg)

        # Check that the comms files were written out.
        received = [os.path.join(self._comms_dir,
                                 x) for x in os.listdir(self._comms_dir)]
        expected = [os.path.join(self._comms_dir, '%s.%d.%s') %
                    ('email', self._id_001, 'pe'),
                    os.path.join(self._comms_dir, '%s.%d.%s') %
                    ('sms', self._id_001, 'pe')]
        msg = 'Comms directory file list error'
        self.assertListEqual(sorted(received), sorted(expected), msg)

        # Cleanup.
        remove_files(received)

    def test_process_no_mts_file(self):
        """Check processing -- no MTS file.
        """
        dry = True
        received = self._pe.process(None, dry=dry)
        expected = []
        msg = 'Processed primary elect should return empty list'
        self.assertListEqual(received, expected, msg)

    @classmethod
    def tearDownClass(cls):
        cls._pe = None
        del cls._pe
        os.removedirs(cls._comms_dir)
        del cls._comms_dir
        del cls._test_file
