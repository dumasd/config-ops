import logging
import unittest
from configops.app import app

logger = logging.getLogger(__name__)


class TestElasticsearchChange(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
