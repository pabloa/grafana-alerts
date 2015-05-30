import unittest

import grafana_alerts


class TestSimple(unittest.TestCase):
    
    def test_failure(self):
        self.assertTrue(False)
