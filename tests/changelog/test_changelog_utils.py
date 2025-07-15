import logging
import unittest
import secrets
import base64
from configops.changelog.changelog_utils import (
    pack_changes,
    unpack_changes,
)

logger = logging.getLogger(__name__)


class TestChangelogUtils(unittest.TestCase):
    def setUp(self):
        # Set up any necessary test data or state
        pass

    def tearDown(self):
        # Clean up any test data or state
        pass

    def test_changes_encrypt_decrypt(self):
        # Example test case
        changes = [
            {
                "namespace": "blue",
                "group": "group",
                "dataId": "config.yaml",
                "format": "yaml",
                "patchContent": "1aadfadf:123213",
            }
        ]
        secret = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
        
        logger.info(f"secret: {secret}")
        changes_bytes = pack_changes(changes, secret)

        _changes = unpack_changes(changes_bytes, secret)
        logger.info(f"changes: {_changes}")
