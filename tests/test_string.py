import logging
import os

logger = logging.getLogger(__name__)


def test_blank():
    a = None

    # logger.info(len(a))
    b = "    "
    assert len(b.strip()) == 0
    logger.info(len(b.strip()))

def test_file():
    f = "/Users/wukai/IdeaProjects/Opensource/config-ops/tests/changelog/changelog-root.yaml"
    logger.info(os.path.isfile(f))
