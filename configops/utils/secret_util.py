import threading, logging, json, os
import botocore
from dataclasses import dataclass
from configops import config as configops_config
import aws_secretsmanager_caching
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

logger = logging.getLogger(__name__)

botocore_lock = threading.Lock()
botocore_client_map = {}


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
            cache_config = (
                aws_secretsmanager_caching.SecretCacheConfig()
            )  # See below for defaults
            cache = aws_secretsmanager_caching.SecretCache(
                config=cache_config, client=client
            )
            botocore_client_map[profile_key] = cache

        return botocore_client_map[profile_key]


def get_secret_data(cfg: map, password_name="password") -> SecretData:
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
    return SecretData(password=cfg[password_name])


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
