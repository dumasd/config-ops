from ops.utils import config_handler, constants
import io
import logging
from jproperties import Properties

logger = logging.getLogger(__name__)


class TestConfigHandler:
    def test_yaml_remove_extra_keys(self):
        current_str = """# commit
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
        full_str = """
        key1: value1
        key2: value2
        nested:
            key3: value3
        list_key:
            - item1
            - item2            
        """
        format1, current, yaml = config_handler.parse_content(current_str)
        format2, full, yaml = config_handler.parse_content(full_str)
        config_handler.yaml_cpx(full, current)
        logging.info("\n%s", config_handler.yaml_to_string(current, yaml))

    def test_yaml_patch(self):
        current_str = """# commit
        key1: value1
        key2: value2
        extra_key: value_extra
        nested:
            key3: value3
            extra_nested_key: value_extra_nested
        list_key:
            - item1
            - item2
            - extra_item
        """
        patch_str = """
        key1: value1_new
        list_key:
            - item1
            - item2            
        """
        format1, current, yaml = config_handler.parse_content(current_str)
        format2, patch, yaml = config_handler.parse_content(patch_str)
        config_handler.yaml_patch(patch, current)
        logging.info("\n%s", config_handler.yaml_to_string(current, yaml))

    def test_parse_content(self):
        cstr = """# comment
vod.system.type = MFC
mfc.detail.es.cluster.server.username = 
mfc.detail.es.cluster.server.password = 
mfc.detail.es.cluster.server.serverName = 
        """
        format, current, yaml = config_handler.parse_content(cstr)
        current["nested.key3"] = "value3_new"
        current["key1"] = 3333
        logger.info(current["nested.key3"])
        logger.info("\n%s", config_handler.properties_to_string(current))

    def test_properties_remove_extra_keys(self):
        current_str = """#comment
        key1=value1
        extra_key=value_extra
        nested.key3=value3
        # comment2222
        # [section]
        nested.key-1.key-1-1=value_prod
        nested.arr[0].key1=aaa1
        nested.arr[0].key2=aaa2
        nested.arr[1].key1=bbb_prod1
        nested.arr[1].key2=bbb_prod2
        """
        full_str = """#comment
        key1=value1
        nested.key3=value3
        # comment2222
        # [section]
        nested.key-1.key-1-1=value_test
        nested.arr[1].key1=bbb_test1
        nested.arr[1].key2=bbb_test2
        """
        f1, current, yml1 = config_handler.parse_content(current_str)
        f2, full, yml2 = config_handler.parse_content(full_str)
        config_handler.properties_cpx(full, current)
        logger.info("\n%s", config_handler.properties_to_string(current))

    def test_properties_patch(self):
        current_str = """#comment
        key1=value1
        extra_key=value_extra
        nested.key3=value3
        # comment2222
        [section]
        nested.key-1.key-1-1=value_prod
        nested.arr[0].key1=aaa1
        nested.arr[0].key2=aaa2
        nested.arr[1].key1=bbb_prod1
        nested.arr[1].key2=bbb_prod2
        """
        patch_str = """#comment
        key1=value1_new
        nested.key3=value3_new
        [section]
        nested.key-1.key-1-1=value_new
        """
        f1, current, yml1 = config_handler.parse_content(current_str)
        f2, patch, yml2 = config_handler.parse_content(patch_str)
        config_handler.properties_patch(patch, current)
        logger.info("\n%s", config_handler.properties_to_string(current))

    def test_jproperties(self):
        current_str = """#comment
        key1=value1
        extra_key=value_extra
        nested.key3=value3
        # comment2222
        nested.key-1.key-1-1=value_prod
        nested.arr[0].key1=aaa1
        nested.arr[0].key2=aaa2
        nested.arr[1].key1=bbb_prod1
        nested.arr[1].key2=bbb_prod2
        """
        p = Properties()
        p.load(current_str, encoding="utf-8")
        output_stream = io.BytesIO()
        p.store(out_stream=output_stream, encoding="utf-8")
        t = output_stream.getvalue()
        logger.info("\n%s", t)
