# AWS secret manager 工具

import threading, logging, json, os
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
        profile_key = "prifile_" + profile
        if profile_key not in botocore_client_map:
            os.environ["AWS_PROFILE"] = profile
            access_key = None
            secret_key = None
            region = None
            if aws_config:
                if "credentials" in aws_config:
                    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = aws_config[
                        "credentials"
                    ]
                if "config" in aws_config:
                    os.environ["AWS_CONFIG_FILE"] = aws_config["config"]

                access_key = aws_config.get("access_key", None)
                secret_key = aws_config.get("secret_key", None)
                region = aws_config.get("region", None)

            client = botocore.session.get_session().create_client(
                "secretsmanager",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
            cache_config = SecretCacheConfig()  # See below for defaults
            cache = SecretCache(config=cache_config, client=client)
            botocore_client_map[profile_key] = cache

        return botocore_client_map[profile_key]


def get_secret_data(cfg: map) -> SecretData:
    secret_mgt = cfg.get("secretmanager", None)
    if secret_mgt:
        aws_secret_mgt = secret_mgt.get("aws", None)
        # 从aws secretmanager获取
        if aws_secret_mgt:
            profile = aws_secret_mgt.get("profile", "default")
            secretid = aws_secret_mgt["secretid"]
            secret_cache = __get_or_create_botocore_cache(profile)
            secret_string = secret_cache.get_secret_string(secretid)
            db_info = json.loads(secret_string)
            return SecretData(password=db_info["password"])
    return SecretData(password=cfg["password"])
