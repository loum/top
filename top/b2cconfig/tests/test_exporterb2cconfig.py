import unittest2
import os

import top


class TestExporterB2CConfig(unittest2.TestCase):

    def setUp(self):
        self._c = top.ExporterB2CConfig()

    def test_init(self):
        """Initialise a ExporterB2CConfig object.
        """
        msg = 'Object is not a top.ExporterB2CConfig'
        self.assertIsInstance(self._c, top.ExporterB2CConfig, msg)

    def test_parse_config(self):
        """Parse comms items from the config.
        """
        config_file = os.path.join('top', 'conf', 'top.conf')

        self._c.set_config_file(config_file)
        self._c.parse_config()

        received = self._c.exporter_loop
        expected = 300
        msg = 'ExporterB2CConfig.exporter_loop error'
        self.assertEqual(received, expected, msg)

        received = self._c.staging_base
        expected = '/var/ftp/pub/nparcel'
        msg = 'ExporterB2CConfig.staging_base error'
        self.assertEqual(received, expected, msg)

        received = self._c.archive_dir
        expected = '/data/top/archive'
        msg = 'ExporterB2CConfig.archive_dir error'
        self.assertEqual(received, expected, msg)

        received = self._c.signature_dir
        expected = os.path.join('/data/www/nparcel/data/signature')
        msg = 'ExporterB2CConfig.signature_dir error'
        self.assertEqual(received, expected, msg)

        received = self._c.file_bu
        expected = {'tolf': 2,
                    'tolf_act': 2,
                    'tolf_nsw': 2,
                    'tolf_qld': 2,
                    'tolf_sa': 2,
                    'tolf_vic': 2,
                    'tolf_wa': 2,
                    'toli': 3,
                    'tolp': 1}
        msg = 'dir.file_bu error'
        self.assertDictEqual(received, expected, msg)

        received = self._c.exporter_dirs
        expected = [os.path.join(os.sep, 'data', 'top', 'exporter')]
        msg = 'dir.exporter_in error'
        self.assertListEqual(received, expected, msg)

        received = self._c.exporter_headers
        expected = {'connote_nbr': ['REF1', 'Ref1'],
                    'item_nbr': ['ITEM_NBR'],
                    'pickup_ts': ['PICKUP_TIME'],
                    'pod_name': ['PICKUP_POD'],
                    'identity_type_id': ['IDENTITY_TYPE'],
                    'identity_type_data': ['IDENTITY_DATA']}
        msg = 'exporter_headers error'
        self.assertDictEqual(received, expected, msg)

        received = self._c.exporter_defaults
        expected = {'identity_type_id': '9'}
        msg = 'exporter_defaults error'
        self.assertDictEqual(received, expected, msg)

        received = self._c.exporter_file_formats
        expected = ['.*_RE[PIF]_\d{14}\.txt$']
        msg = 'exporter.file_formats error'
        self.assertListEqual(received, expected, msg)

        received = self._c.exporter_fields
        expected = {'tolp': '0,1,2,3,4,5,6',
                    'tolf': '0,1,2,3,4,5,6',
                    'toli': '0,1,2,3,4,5,6,7'}
        msg = 'exporter_fields error'
        self.assertDictEqual(received, expected, msg)

        received = self._c.business_units
        expected = {'priority': 1, 'fast': 2, 'ipec': 3}
        msg = 'business_units config section error'
        self.assertDictEqual(received, expected, msg)

        received = self._c.cond
        expected = {'tolp': '000100000000010110',
                    'tolf': '000101100000010110',
                    'toli': '100010000000010110'}
        msg = 'ExporterB2CConfig.cond error'
        self.assertDictEqual(received, expected, msg)

    def tearDown(self):
        del self._c
