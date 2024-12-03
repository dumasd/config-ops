import yaml
import hashlib


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
