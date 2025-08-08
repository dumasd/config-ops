from typing import Optional
import yaml
import hashlib
import msgpack
import base64
import logging
from configops.utils.secret_util import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


def __clean_string__(value: str) -> str:
    """
    Clean a string by removing leading and trailing whitespace and converting it to lowercase.

    Args:
        s (str): The string to clean.

    Returns:
        str: The cleaned string.
    """
    return value.replace(" ", "").replace("\n", "").replace("\t", "").replace(";", "")


def __normalize_change__(change):
    new_change = {}
    for k, v in change.items():
        if (k == "query" or k == "body") and isinstance(v, str):
            new_change[k] = __clean_string__(v)
        else:
            new_change[k] = v
    return new_change


def get_change_set_checksum(changes):
    changes_str = yaml.dump(changes, sort_keys=True)
    return hashlib.sha256(changes_str.encode()).hexdigest()


def get_change_set_checksum_new(changes) -> str:
    """
    Calculate the checksum of a changeset dictionary.

    Args:
        changes (dict): The changeset dictionary to calculate the checksum for.

    Returns:
        str: The SHA-256 checksum of the changeset.
    """
    new_changes = []
    for change in changes:
        change_str = yaml.dump(__normalize_change__(change), sort_keys=True)
        change_hash = hashlib.sha256(change_str.encode()).hexdigest()
        new_changes.append(change_hash)

    return hashlib.sha256("".join(new_changes).encode()).hexdigest()


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
