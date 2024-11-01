# AWS secret manager 工具

import threading, logging, json
import botocore
import botocore.session
from dataclasses import dataclass
from configops import config as configops_config
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig

logger = logging.getLogger(__name__)

botocore_lock = threading.Lock()
botocore_client_map = {}


@dataclass
class SecretData:
    password: str


def __get_or_create_botocore_cache(profile: str) -> SecretCache:
    """Get or create botocore cache cleint.

    :type profile: str
    :param profile: Aws config profole

    :rtype: aws_secretsmanager_caching.SecretCache
    :return: aws_secretsmanager_caching
    """
    aws_config = configops_config.get_aws_cfg()
    with botocore_lock:
        if profile not in botocore_client_map:
            aws_env_vars = {}
            aws_env_vars["AWS_DEFAULT_PROFILE"] = profile
            if aws_config:
                if "credentials" in aws_config:
                    aws_env_vars["AWS_SHARED_CREDENTIALS_FILE"] = aws_config[
                        "credentials"
                    ]
                if "config" in aws_config:
                    aws_env_vars["AWS_CONFIG_FILE"] = aws_config["config"]

            client = botocore.session.get_session(aws_env_vars).create_client(
                "secretsmanager"
            )
            cache_config = SecretCacheConfig()  # See below for defaults
            cache = SecretCache(config=cache_config, client=client)
            botocore_client_map[profile] = cache
            return cache


def get_secret_data(cfg: map) -> SecretData:
    secret_mgt = cfg.get("secretmanager", None)
    aws_config = configops_config.get_aws_cfg()
    logger.info(f"aws info {aws_config}")
    if secret_mgt:
        aws_secret_mgt = secret_mgt.get("aws", None)
        # 从aws secretmanager获取
        if aws_secret_mgt:
            try:
                profile = aws_secret_mgt.get("profile", "default")
                secretid = aws_secret_mgt["secretid"]
                secret_cache = __get_or_create_botocore_cache(profile)
                secret_string = secret_cache.get_secret_string(secretid)
                db_info = json.loads(secret_string)
                return SecretData(password=db_info["password"])
            except Exception as e:
                logger.warning(f"Search . {e}")

    return SecretData(password=cfg["password"])
