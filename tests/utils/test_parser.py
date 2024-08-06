from nacos_config.utils import parser, constants
import io
import logging

logger = logging.getLogger(__name__)

class TestParser:
    def test_yaml_remove_extra_keys(self):
        
        current_str= """# commit
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
        parser.yaml_remove_extra_keys(full, current)
        logging.info('\n%s', parser.yaml_to_string(current, yaml))
    
    def test_yaml_patch(self):
        current_str= """# commit
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
        logging.info('\n%s', parser.yaml_to_string(current, yaml))
        