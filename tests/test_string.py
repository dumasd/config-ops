import logging

logger = logging.getLogger(__name__)


def test_blank():
    a = None

    # logger.info(len(a))
    b = "    "
    assert len(b.strip()) == 0
    logger.info(len(b.strip()))
