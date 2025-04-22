import yaml
import hashlib
import msgpack
import base64
from configops.utils.secret_util import encrypt_data, decrypt_data


def get_change_set_checksum(changes):
    changes_str = yaml.dump(changes, sort_keys=True)
    return hashlib.sha256(changes_str.encode()).hexdigest()


def is_ctx_included(contexts: str, changeSetCtx: str) -> bool:
    if contexts:
        contextList = contexts.split(",")
        if changeSetCtx:
            changeSetCtxList = changeSetCtx.split(",")
            for changeSetCtx in changeSetCtxList:
                if changeSetCtx in contextList:
                    return True
        return False
    else:
        return True


def pack_encrypt_changes(changes, secret: str) -> bytes:
    packed_data = msgpack.packb(changes)
    secret_key = base64.b64decode(secret)
    return encrypt_data(packed_data, secret_key)


def unpack_encrypt_changes(changes_bytes: bytes, secret: str):
    secret_key = base64.b64decode(secret)
    return msgpack.unpackb(decrypt_data(changes_bytes, secret_key))
