import unittest2
import os

import top


class TestPodB2CConfig(unittest2.TestCase):

    def setUp(self):
        self._c = top.PodB2CConfig()

    def test_init(self):
        """Initialise a PodB2CConfig object.
        """
        msg = 'Object is not a top.PodB2CConfig'
        self.assertIsInstance(self._c, top.PodB2CConfig, msg)

    def test_parse_config(self):
        """Parse comms items from the config.
        """
        config_file = os.path.join('top', 'conf', 'top.conf')

        self._c.set_config_file(config_file)
        self._c.parse_config()

        received = self._c.archive_dir
        expected = '/data/top/archive'
        msg = 'podb2cconfig.archive_dir error'
        self.assertEqual(received, expected, msg)

        received = self._c.pod_translator_loop
        expected = 600
        msg = 'podb2cconfig.pod_translator_loop error'
        self.assertEqual(received, expected, msg)

        received = self._c.pod_dirs
        expected = [os.path.join(os.sep,
                                 'var',
                                 'ftp',
                                 'pub',
                                 'nparcel',
                                 'parcelpoint',
                                 'in')]
        msg = 'podb2cconfig.pod_in error'
        self.assertListEqual(received, expected, msg)

        received = self._c.out_dir
        expected = os.path.join(os.sep,
                                'var',
                                'ftp',
                                'pub',
                                'nparcel',
                                'fast',
                                'out')
        msg = 'podb2cconfig.out_dir error'
        self.assertEqual(received, expected, msg)

        received = self._c.file_formats
        expected = ['.*_REF_\\d{14}\\.txt$']
        msg = 'podb2cconfig.file_formats error'
        self.assertListEqual(received, expected, msg)

    def tearDown(self):
        del self._c
