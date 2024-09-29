import io
import logging
import configparser
import configobj
import json
from configops.utils import constants
from ruamel import yaml as ryaml
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def validate_yaml(content):
    """
    Validate yaml
    """
    try:
        yaml = ryaml.YAML()
        yaml.preserve_quotes = True
        yaml.load(content)
        return True, "OK"
    except Exception as ex:
        logger.error(f"Yaml is invalid:{ex}")
        return False, f"Yaml is invalid: {ex}"


def validate_properties(content):
    try:
        configobj.ConfigObj(
            io.StringIO(content),
            encoding="utf-8",
            list_values=False,
            raise_errors=True,
            write_empty_values=True,
        )
        return True, "OK"
    except configparser.Error as e:
        logger.error(f"Properties is invalid:{e}")
        return False, f"Properties is invalid:{e}"


def validate_xml(content):
    try:
        ET.fromstring(content)
        return True, "OK"
    except ET.ParseError as e:
        logger.error(f"XML is invalid:{e}")
        return False, f"XML is invalid:{e}"


def validate_json(content):
    try:
        json.loads(content)
        return True, "OK"
    except json.JSONDecodeError as e:
        logger.error(f"JSON is invalid:{e}")
        return False, f"JSON is invalid:{e}"


def validate_content(content, format):
    if format == constants.YAML:
        return validate_yaml(content)
    if format == constants.PROPERTIES:
        return validate_properties(content)
    if format == constants.JSON:
        return validate_json(content)
    if format == constants.XML:
        return validate_xml(content)
    else:
        return True, "Unknown format"
