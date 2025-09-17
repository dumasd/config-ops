import logging
from ruamel import yaml as ryaml
from configops.changelog import changelog_utils, nacos_change
from jsonschema import Draft7Validator, ValidationError
import unittest
from configops.utils.constants import SystemType

logger = logging.getLogger(__name__)


class TestNacosChange(unittest.TestCase):

    def setUp(self):
        pass

    def test_nacos_checksum(self):
        changelog_file = "tests/changelog/nacos/changelog-1.0.yaml"
        nacos_change_log = nacos_change.NacosChangeLog(changelog_file=changelog_file, app=None)
        for change_set_obj in nacos_change_log.change_set_list:
            checksum = changelog_utils.get_change_set_checksum_v2(
                change_set_obj["changes"], SystemType.NACOS
            )
            logger.info(f"change_set_id: {change_set_obj['id']}, checksum: {checksum}")

    def test_schema_validation(self):
        yaml_content = """
nacosChangeLog:
  - include:
      file: changelog-1.0.0.yaml
  - changeSet:
      id: 1    # ID不能重复
      author: bruce.wu 
      comment: 注释
      ignore: false
      changes:
        # namespace+group+dataId不能重复
        - namespace: blue   
          group: group
          dataId: config.yaml
          format: yaml  # 目前只支持yaml和properties
          patchContent: |-
            spring:
              application:
                name: blue
          deleteContent: |-
            notice:
        - namespace: blue
          group: group
          dataId: config.properties
          format: properties
          patchContent: |-

          deleteContent: |-
"""
        try:
            yaml = ryaml.YAML()
            yaml.preserve_quotes = True
            data = yaml.load(yaml_content)
            validator = Draft7Validator(nacos_change.schema)
            validator.validate(data)

            arr = data["nacosChangeLog"]
            for item in arr:
                logger.info(item)

        except ValidationError as e:
            logger.error(f"YAML 数据校验失败 {e}")
