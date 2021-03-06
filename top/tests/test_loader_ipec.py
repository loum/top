import unittest2

import top

FILE_BU = {'tolp': '1', 'tolf': '2', 'toli': '3'}
COND_MAP_IPEC = {'item_number_excp': True}
VALID_CONNOTE = '218501217863'
VALID_ITEM_NUMBER = 'abcdefghijklmnopqrstuvwxyz012345'
VALID = """218501217863          YMLML11TOLI130413  Diane Donohoe                           31 Bridge st,                 Lane Cove,                    Australia Other               2066                                                                                                                 Diane Donohoe                             Bally                         Hong Kong Other                                                               4156536111     N031                                                                                                                                   00001000001                                                                      Parcels Overnight                   Rm 603, Yeekuk Industrial,, 55Li chi kok, HK.               loumar@tollgroup.com                                        0431601245                 N031                               abcdefghijklmnopqrstuvwxyz012345                                        HONG KONG                     AUSTRALIA                                                                                                                                                                                                      1  NS                                               """
MISSING_BARCODE = """218501217863          YMLML11TOLI130413  Diane Donohoe                           31 Bridge st,                 Lane Cove,                    Australia Other               2066                                                                                                                 Diane Donohoe                             Bally                         Hong Kong Other                                                                              N031                                                                                                                                   00001000001                                                                      Parcels Overnight                   Rm 603, Yeekuk Industrial,, 55Li chi kok, HK.                                                                                                      N031                               abcdefghijklmnopqrstuvwxyz012345                                        HONG KONG                     AUSTRALIA                                                                                                                                                                                                      1  NS                                               """
MISSING_CONNOTE = """                      YMLML11TOLI130413  Diane Donohoe                           31 Bridge st,                 Lane Cove,                    Australia Other               2066                                                                                                                 Diane Donohoe                             Bally                         Hong Kong Other                                                               4156536111     N031                                                                                                                                   00001000001                                                                      Parcels Overnight                   Rm 603, Yeekuk Industrial,, 55Li chi kok, HK.                                                                                                      N031                                                                       HONG KONG                     AUSTRALIA                                                                                                                                                                                                      1  NS                                               """
MISSING_ITEM = """218501217863          YMLML11TOLI130413  Diane Donohoe                           31 Bridge st,                 Lane Cove,                    Australia Other               2066                                                                                                                 Diane Donohoe                             Bally                         Hong Kong Other                                                               4156536111     N031                                                                                                                                   00001000001                                                                      Parcels Overnight                   Rm 603, Yeekuk Industrial,, 55Li chi kok, HK.                                                                                                      N031                                                                                                       HONG KONG                     AUSTRALIA                                                                                                                                                                                                      1  NS                                               """
MANUFACTURED_BC_LINE = """3142357006912345      YMLML11TOLI130413  Diane Donohoe                           31 Bridge st,                 Lane Cove,                    Australia Other                                                                                                                                    Diane Donohoe                             Bally                         Hong Kong Other                                                               000931423570069N031                                                                                                                                   00001000001                                                                      Parcels Overnight                   Rm 603, Yeekuk Industrial,, 55Li chi kok, HK.                                                                                                      N031                               abcdefghijklmnopqrstuvwxyz012345                                        HONG KONG                     AUSTRALIA                                                                                                                                                                                                      1  NS                                               """
MANUFACTURED_BC_UPD_LINE = """3142357006912345      YMLML11TOLI130413  Diane Donohoe                           31 Bridge st,                 Lane Cove,                    Australia Other                                                                                                                                    Diane Donohoe                             Bally                         Hong Kong Other                                                               000931423570069N031                                                                                                                                   00001000001                                                                      Parcels Overnight                   Rm 603, Yeekuk Industrial,, 55Li chi kok, HK.                                                                                                      N032                               abcdefghijklmnopqrstuvwxyz012345                                        HONG KONG                     AUSTRALIA                                                                                                                                                                                                      1  NS                                               """


class TestLoaderIpec(unittest2.TestCase):
    """Loader test cases specific to Ipec loader scenarios.
    """

    @classmethod
    def setUpClass(cls):
        cls._ldr = top.Loader()
        cls._job_ts = cls._ldr.db.date_now()

    def test_processor_valid(self):
        """Process raw T1250 line -- missing barcode.
        """
        # Seed the Agent Id.
        agent_fields = {'code': 'N031'}
        self._ldr.db(self._ldr.db._agent.insert_sql(agent_fields))

        msg = 'T1250 record should process OK'
        received = self._ldr.process(self._job_ts,
                                     VALID,
                                     FILE_BU.get('toli'),
                                     COND_MAP_IPEC)
        self.assertTrue(received, msg)

        # Check that the item_number value is honored.
        sql = """SELECT item_nbr
FROM job_item
WHERE connote_nbr = '%s'""" % VALID_CONNOTE
        self._ldr.db(sql)
        received = self._ldr.db.row
        expected = ('%s' % VALID_ITEM_NUMBER, )
        msg = ('Expected Item Number "%s" query not returned' %
               VALID_ITEM_NUMBER)
        self.assertEqual(received, expected, msg)

        # Restore DB state.
        self._ldr.db.connection.rollback()

    def test_processor_missing_barcode(self):
        """Process raw T1250 line -- missing barcode.
        """
        # Seed the Agent Id.
        agent_fields = {'code': 'N031'}
        self._ldr.db(self._ldr.db._agent.insert_sql(agent_fields))

        msg = 'T1250 record with missing barcode should fail'
        received = self._ldr.process(self._job_ts,
                                     MISSING_BARCODE,
                                     FILE_BU.get('toli'),
                                     COND_MAP_IPEC)
        self.assertFalse(received, msg)

        # Restore DB state.
        self._ldr.db.connection.rollback()

    def test_processor_missing_connote(self):
        """Process raw T1250 line -- missing connote.
        """
        # Seed the Agent Id.
        agent_fields = {'code': 'N031'}
        self._ldr.db(self._ldr.db._agent.insert_sql(agent_fields))

        msg = 'T1250 record with missing connote should fail'
        received = self._ldr.process(self._job_ts,
                                     MISSING_CONNOTE,
                                     FILE_BU.get('toli'),
                                     COND_MAP_IPEC)
        self.assertFalse(received, msg)

        # Restore DB state.
        self._ldr.db.connection.rollback()

    def test_processor_missing_item_number(self):
        """Process raw T1250 line -- missing item_number.
        """
        # Seed the Agent Id.
        agent_fields = {'code': 'N031'}
        self._ldr.db(self._ldr.db._agent.insert_sql(agent_fields))

        msg = 'T1250 record with missing item_number should fail'
        received = self._ldr.process(self._job_ts,
                                     MISSING_ITEM,
                                     FILE_BU.get('toli'),
                                     COND_MAP_IPEC)
        self.assertFalse(received, msg)

        # Restore DB state.
        self._ldr.db.connection.rollback()

    def test_processor_manufactured_connote(self):
        """Process valid raw T1250 line with manufactured barcode.
        """
        # Seed the Agent Id.
        agent_fields = [{'code': 'N031'},
                        {'code': 'N032'}]
        for agent_field in agent_fields:
            self._ldr.db(self._ldr.db._agent.insert_sql(agent_field))

        # First, create a manufactured barcode value.
        msg = 'Manufactured barcode creation failed -- no barcode'
        self.assertTrue(self._ldr.process(self._job_ts,
                                          MANUFACTURED_BC_LINE,
                                          FILE_BU.get('toli'),
                                          COND_MAP_IPEC), msg)

        # Now the manufactured barcode value update.
        msg = 'Manufactured barcode creation failed -- existing barcode'
        self.assertTrue(self._ldr.process(self._job_ts,
                                          MANUFACTURED_BC_UPD_LINE,
                                          FILE_BU.get('toli'),
                                          COND_MAP_IPEC), msg)

        # Restore DB state.
        self._ldr.db.connection.rollback()

    def test_jobitem_table_column_map_for_a_valid_raw_record_ipec(self):
        """Parse Ipec T1250 line and map "jobitem" table elements.
        """
        fields = self._ldr.parser.parse_line(VALID)
        received = self._ldr.table_column_map(fields,
                                              top.loader.JOB_ITEM_MAP,
                                              COND_MAP_IPEC)
        # Null out the time created.
        received['created_ts'] = None
        expected = {'connote_nbr': '218501217863',
                    'item_nbr': 'abcdefghijklmnopqrstuvwxyz012345',
                    'consumer_name': 'Diane Donohoe',
                    'email_addr': 'loumar@tollgroup.com',
                    'phone_nbr': '0431601245',
                    'pieces': '00001',
                    'status': 1,
                    'created_ts': None}
        msg = 'Valid record "jobitem" table translation error'
        self.assertDictEqual(received, expected, msg)

    @classmethod
    def tearDownClass(cls):
        cls._ldr = None
        cls._job_ts = None
