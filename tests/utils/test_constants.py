from configops.utils import config_handler, constants
import io
import logging

logger = logging.getLogger(__name__)


class TestConstants:

    def test_version_compare(self):
        files = [
            "oper-sys-admin-changelog-db-v6.0.0.0-02.yaml",
            "oper-sys-admin-changelog-db-v6.0.0.0-03.yaml",
            "oper-sys-admin-changelog-db-v6.0.0.0-01.yaml",
            "oper-sys-admin-changelog-db-v6.1.1.1-02.yaml",
            "oper-sys-admin-changelog-db-v6.0.2.1-01.yaml",
            "oper-sys-admin-changelog-db-v6.0.0.0-04.yaml",
        ]
        sorted_files = sorted(files, key=constants.extract_version)
        logger.info(f"sorted files: {sorted_files}")
