from ops.utils import parser, constants
import io
import logging

logger = logging.getLogger(__name__)


class TestParser:
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
        format1, current, yaml = parser.parse_content(current_str)
        format2, full, yaml = parser.parse_content(full_str)
        parser.yaml_cpx(full, current)
        logging.info("\n%s", parser.yaml_to_string(current, yaml))

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
        format1, current, yaml = parser.parse_content(current_str)
        format2, patch, yaml = parser.parse_content(patch_str)
        parser.yaml_patch(patch, current)
        logging.info("\n%s", parser.yaml_to_string(current, yaml))

    def test_parse_content(self):
        cstr = """# comment
        key1=value1
        extra_key=value_extra
        nested.key3=value3
        # comment2222
        nested.key-1.key-1-1=valueccc
        nested.arr[0].key1=aaa1
        nested.arr[0].key2=aaa2
        nested.arr[1].key1=bbb1
        nested.arr[1].key2=bbb2
        """
        format, current, yaml = parser.parse_content(cstr)
        current["nested.key3"] = "value3_new"
        current["key1"] = 3333
        logger.info(current["nested.key3"])
        logger.info("\n%s", parser.properties_to_string(current))

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
        f1, current, yml1 = parser.parse_content(current_str)
        f2, full, yml2 = parser.parse_content(full_str)
        parser.properties_cpx(full, current)
        logger.info("\n%s", parser.properties_to_string(current))

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
        f1, current, yml1 = parser.parse_content(current_str)
        f2, patch, yml2 = parser.parse_content(patch_str)
        parser.properties_patch(patch, current)
        logger.info("\n%s", parser.properties_to_string(current))
