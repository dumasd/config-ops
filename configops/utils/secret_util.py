import threading, logging, json, os
import botocore
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from dataclasses import dataclass
from types import SimpleNamespace

import botocore.session
from configops import config as configops_config
import aws_secretsmanager_caching
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

logger = logging.getLogger(__name__)

botocore_lock = threading.Lock()
botocore_client_map = {}

DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_PROFILE = "default"


def _get_aws_creds(aws_cfg) -> tuple[SimpleNamespace, str]:
    access_key = aws_cfg.get("access_key")
    secret_key = aws_cfg.get("secret_key")
    region = aws_cfg.get("region", DEFAULT_AWS_REGION)
    profile = aws_cfg.get("profile", DEFAULT_PROFILE)
    if access_key and secret_key:
        return SimpleNamespace(access_key=access_key, secret_key=secret_key), region

    global_aws_config = configops_config.get_aws_cfg()
    if global_aws_config:
        if "credentials" in global_aws_config:
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = global_aws_config["credentials"]
        if "config" in global_aws_config:
            os.environ["AWS_CONFIG_FILE"] = global_aws_config["config"]
        access_key = global_aws_config.get("access_key")
        secret_key = global_aws_config.get("secret_key")
        region = global_aws_config.get("region", DEFAULT_AWS_REGION)

        if access_key and secret_key:
            return SimpleNamespace(access_key=access_key, secret_key=secret_key), region

    session = botocore.session.Session(profile=profile)
    credentials = session.get_credentials()
    creds = credentials.get_frozen_credentials()
    return (
        SimpleNamespace(access_key=creds.access_key, secret_key=creds.secret_key),
        region,
    )


@dataclass
class SecretData:
    password: str


def __get_or_create_botocore_cache(
    profile: str,
) -> aws_secretsmanager_caching.SecretCache:
    """Get or create botocore cache cleint.

    :type profile: str
    :param profile: Aws config profole

    :rtype: aws_secretsmanager_caching.SecretCache
    :return: aws_secretsmanager_caching
    """
    with botocore_lock:
        profile_key = "prifile_" + profile
        if profile_key not in botocore_client_map:
            creds, region = _get_aws_creds({"profile": profile})
            client = botocore.session.Session(profile=profile).create_client(
                "secretsmanager",
                aws_access_key_id=creds.access_key,
                aws_secret_access_key=creds.secret_key,
                region_name=region,
            )
            cache_config = (
                aws_secretsmanager_caching.SecretCacheConfig()
            )  # See below for defaults
            cache = aws_secretsmanager_caching.SecretCache(
                config=cache_config, client=client
            )
            botocore_client_map[profile_key] = cache

        return botocore_client_map[profile_key]


def get_secret_data(cfg: map, password_name="password") -> SecretData:
    secret_manager_cfg = cfg.get("secretmanager", None)
    if secret_manager_cfg:
        aws_secret_manager_cfg = secret_manager_cfg.get("aws", None)
        if aws_secret_manager_cfg:  # Fetch password from AWS secretmanager
            profile = aws_secret_manager_cfg.get("profile", "default")
            secretid = aws_secret_manager_cfg["secretid"]
            secret_cache = __get_or_create_botocore_cache(profile)
            secret_string = secret_cache.get_secret_string(secretid)
            db_info = json.loads(secret_string)
            return SecretData(password=db_info["password"])
    return SecretData(password=cfg.get(password_name))


def get_aws_request_headers(
    aws_cfg: dict, method, service, request_url, payload
) -> dict:
    """
    Generate AWS request headers for signing requests.

    :param aws_cfg: AWS configuration dictionary containing access_key, secret_key, region, etc.
    :param method: HTTP method (e.g., 'GET', 'POST')
    :param service: AWS service name (e.g., 'neptune-db')
    :param request_url: The URL of the request to be signed
    :param payload: The request payload (data for POST, params for GET)
    :return: A dictionary of headers to be included in the request"""

    if not aws_cfg or not aws_cfg.get("enabled", False):
        return {}
    creds, region = _get_aws_creds(aws_cfg)
    data = payload if method == "POST" else None
    params = payload if method == "GET" else None
    request = AWSRequest(method=method, url=request_url, data=data, params=params)
    SigV4Auth(creds, service, region).add_auth(request)
    return request.headers.items()


def encrypt_data(data: bytes, secret_key: bytes) -> bytes:
    """使用 AES CBC 模式加密数据"""
    # 填充数据至 AES 块大小的倍数
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()
    iv = os.urandom(16)
    cipher = Cipher(
        algorithms.AES(secret_key), modes.CBC(iv), backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # 返回 IV 和加密数据（IV 存储在加密数据的前面）
    return iv + encrypted_data


def decrypt_data(encrypted_data: bytes, secret_key: bytes) -> bytes:
    """使用 AES CBC 模式解密数据"""
    iv = encrypted_data[:16]  # 提取 IV
    cipher_data = encrypted_data[16:]  # 提取加密数据

    cipher = Cipher(
        algorithms.AES(secret_key), modes.CBC(iv), backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(cipher_data) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()
    return unpadded_data
