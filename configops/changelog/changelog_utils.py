import json
from typing import Optional
import yaml
import hashlib
import msgpack
import base64
import logging
from configops.utils import config_handler
from configops.utils.constants import SystemType, UNKNOWN
from configops.utils.secret_util import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

CHECKSUM_VERSION = "2"


def __clean_string__(value: str) -> str:
    """
    Clean a string by removing leading and trailing whitespace and converting it to lowercase.

    Args:
        s (str): The string to clean.

    Returns:
        str: The cleaned string.
    """
    return value.replace(" ", "").replace("\n", "").replace("\t", "").replace(";", "")


def get_change_set_checksum(changes):
    changes_str = yaml.dump(changes, sort_keys=True)
    return hashlib.sha256(changes_str.encode()).hexdigest()


def get_change_set_checksum_v2(changes, system_type: SystemType) -> str:
    new_changes = changes
    if system_type == SystemType.NACOS:
        new_changes = []
        for change in changes:
            new_change = change.copy()
            patch_content = change.get("patchContent", "")
            delete_content = change.get("deleteContent", "")
            if patch_content:
                try:
                    parsed_format, patch_obj, _ = config_handler.parse_content(content=patch_content, format=change.get("format"))
                    if parsed_format != UNKNOWN:
                        patch_content = json.dumps(patch_obj, sort_keys=True, ensure_ascii=False)
                except Exception:
                    logger.warning(f"Error parsing patchContent when calculate checksum: {patch_content}")

            if delete_content:
                try:
                    parsed_format, delete_obj, _ = config_handler.parse_content(content=delete_content, format=change.get("format"))
                    if parsed_format != UNKNOWN:
                        delete_content = json.dumps(delete_obj, sort_keys=True, ensure_ascii=False)
                except Exception:
                    logger.warning(f"Error parsing deleteContent when calculate checksum: {delete_content}")

            new_change["patchContent"] = patch_content
            new_change["deleteContent"] = delete_content
            new_changes.append(new_change)
    elif system_type == SystemType.ELASTICSEARCH:
        new_changes = []
        for change in changes:
            new_change = change.copy()
            body = change.get("body")
            if body:
                new_change["body"] = __clean_string__(body)
            new_changes.append(new_change)
    elif system_type == SystemType.GRAPHDB:
        new_changes = []
        for change in changes:
            new_change = change.copy()
            query = change.get("query")
            if query:
                new_change["query"] = __clean_string__(query)
            new_changes.append(new_change)

    checksum_changes = []
    for change in new_changes:
        change_str = json.dumps(change, sort_keys=True, ensure_ascii=False)
        change_hash = hashlib.sha256(change_str.encode()).hexdigest()
        checksum_changes.append(change_hash)
    return CHECKSUM_VERSION + ":" +hashlib.sha256("".join(checksum_changes).encode()).hexdigest()


def is_ctx_included(contexts: str, change_set_ctx: str) -> bool:
    if contexts:
        context_list = contexts.split(",")
        if change_set_ctx:
            change_set_ctx_list = change_set_ctx.split(",")
            for change_set_ctx in change_set_ctx_list:
                if change_set_ctx in context_list:
                    return True
        return False
    else:
        return True


def pack_changes(changes, secret: Optional[str]) -> bytes:
    packed_data = msgpack.packb(changes)
    if secret:
        secret_key = base64.b64decode(secret)
        return encrypt_data(packed_data, secret_key)
    return packed_data


def unpack_changes(changes_bytes: bytes, secret: Optional[str]):
    if secret:
        try:
            secret_key = base64.b64decode(secret)
            return msgpack.unpackb(decrypt_data(changes_bytes, secret_key))
        except Exception as e:
            logger.warning(f"Error decrypting changes: {e}")
    return msgpack.unpackb(changes_bytes, raw=True)
