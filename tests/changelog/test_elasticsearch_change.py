import logging
import unittest
from configops.changelog import changelog_utils
from configops.changelog.elasticsearch_change import ElasticsearchChangelog
from configops.utils.constants import SystemType


logger = logging.getLogger(__name__)


class TestElasticsearchChangeLog(unittest.TestCase):
    def setUp(self):
        # Set up any necessary test data or state
        pass

    def tearDown(self):
        # Clean up any test data or state
        pass

    def test_elasticsearch_checksum(self):
        changelog_file = "tests/changelog/elasticsearch/changelog-root.yaml"
        es_change_log = ElasticsearchChangelog(changelog_file=changelog_file, app=None)
        for change_set_obj in es_change_log.change_set_list:
            checksum = changelog_utils.get_change_set_checksum_v2(
                change_set_obj["changes"], SystemType.ELASTICSEARCH
            )
            logger.info(f"change_set_id: {change_set_obj['id']}, checksum: {checksum}")
