from ops.utils import config_validator, constants
import logging

logger = logging.getLogger(__name__)


class TestConfigValidator:
    def test_validate(self):
        str1 = """# comment
        key1: value1
        key2: value2
        extra_key: value_extra  # 这个键值对在 full_config.yaml 中不存在
        nested:
            key3: value3
            extra_nested_key: value_extra_nested  # 这个键值对在 full_config.yaml 中不存在
        list_key:
            - item1
            - item2
            - extra_item  # 这个项在 full_config.yaml 中不存在
        """
        b, msg = config_validator.validate_content(str1, constants.YAML)
        logger.info(f"validate bool:{b}, msg:{msg}")
        assert b

        str1 = """ #commont
        j2cache.L1.provider_class = caffeine
        j2cache.L2.provider_class = io.github.novareseller.cache.support.redis.SpringRedisProvider
        # tafeaf
        j2cache.L2.config_section = redis
        """
        b, msg = config_validator.validate_content(str1, constants.PROPERTIES)
        logger.info(f"validate bool:{b}, msg:{msg}")
        assert b

        str1 = """<?xml version="1.0" encoding="UTF-8"?>
        <root>
            <!-- log path -->
            <key>value</key>
        </root>
        """
        b, msg = config_validator.validate_content(str1, constants.XML)
        logger.info(f"validate bool:{b}, msg:{msg}")
        assert b

        str1 = """
         {"key": "value", "key2": ["1", "2"]}
        """
        b, msg = config_validator.validate_content(str1, constants.JSON)
        logger.info(f"validate bool:{b}, msg:{msg}")
        assert b