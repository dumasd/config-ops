

import io
import logging
import json
from configops.utils import secret_util

logger = logging.getLogger(__name__)

class TestSecretUtil:

    def test_generate_password(self):
        p = secret_util.generate_password(length=16, contain_special=False)
        logger.info(f"pass: {p}")
        jsons = json.dumps("aaaa", ensure_ascii=False)
        logger.info(f"jsons: {jsons}")
