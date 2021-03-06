import unittest2
import os

import top


class TestStopParser(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._sp = top.StopParser()
        test_dir = os.path.join('top', 'tests', 'files')
        test_file = 'TCD_Deliveries_20140207111019.DAT'
        cls._test_file = os.path.join(test_dir, test_file)

    def test_init(self):
        """Initialise a StopParser object.
        """
        msg = 'Object is not an top.StopParser'
        self.assertIsInstance(self._sp, top.StopParser, msg)

    def test_read(self):
        """Read in the sample csv.
        """
        old_in_files = list(self._sp.in_files)
        self._sp.set_in_files([self._test_file, self._test_file])
        self._sp.read()

        # Check the size of the items parsed.
        received = self._sp.size
        expected = 2953
        msg = 'Size of items parsed error'
        self.assertEqual(received, expected, msg)

        # Return known connote.
        received = self._sp.connote_lookup('7179050262726')
        msg = 'Known connote should not return None'
        self.assertIsNotNone(received)

        # Return multi-item connote -- connote only search.
        received = self._sp.connote_lookup('7179050262727')
        msg = 'Connote (multi-item, connote search) should match'
        self.assertIsNotNone(received)

        # Return multi-item connote -- connote/item_nbr search.
        received = self._sp.connote_lookup('7179050262727')
        msg = 'Multi-item connote (connote/item search) should match'
        self.assertIsNotNone(received)

        # Return unknown connote.
        received = self._sp.connote_lookup('banana')
        msg = 'Unknown connote should return None'
        self.assertIsNone(received)

        # Check delivered.
        received = self._sp.connote_delivered('7179050262')
        msg = 'Undelivered connote should return False'
        self.assertFalse(received)

        # Check delivered.
        received = self._sp.connote_delivered('7179050262736')
        msg = 'Delivered connote should return True'
        self.assertTrue(received)

        # Check delivered -- connote/item search.
        received = self._sp.connote_delivered('7179050246612',
                                              '00393403250084592526')
        msg = 'Delivered connote/item should return True'
        self.assertTrue(received)

        # Check undelivered -- connote/item search.
        received = self._sp.connote_delivered('7179050246612',
                                              '003934032500845925xx')
        msg = 'Undelivered connote/item should return False'
        self.assertFalse(received)

        # ... and purge.
        self._sp.purge()

        # Return previously-known connote.
        received = self._sp.connote_lookup('ARTZ023438')
        msg = 'Known connote should now return None'
        self.assertIsNone(received)

        # Cleanup.
        self._sp.set_in_files(old_in_files)

    @classmethod
    def tearDownClass(cls):
        cls._sp = None
        del cls._sp
