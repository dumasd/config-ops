import logging
from ruamel import yaml as ryaml
from ops.changelog import nacos_change
from ops.utils import nacos_client
from jsonschema import Draft7Validator, ValidationError
import json
import unittest
from ops.app import app

logger = logging.getLogger(__name__)


class TestNacosChange(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

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

    def test_nacos_change(self):
        nacosChangeLog = nacos_change.NacosChangeLog(
            changelogFile="/Users/wukai/IdeaProjects/Opensource/config-ops/tests/changelog/master.yaml"
        )
        logger.info(nacosChangeLog.changeSets)
        client = nacos_client.ConfigOpsNacosClient(
            server_addresses="http://127.0.0.1:8848",
            username="nacos",
            password="nacos",
        )
        nacosChangeLog.fetch_current(client, "default")
