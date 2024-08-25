from ops.utils.nacos_client import ConfigOpsNacosClient
import logging

logger = logging.getLogger(__name__)
server_addresses = "http://localhost:8848"
username = "nacos"
password = "nacos"
"""
class TestNacosClient:

    def test_list_namespace(self):
        client = ConfigOpsNacosClient(
            server_addresses=server_addresses,
            username=username,
            password=password,
        )
        namespace_list = client.list_namespace()
        logger.info(f"namespaceList:{namespace_list}")

    def test_get_configs(self):
        client = ConfigOpsNacosClient(
            server_addresses=server_addresses,
            username=username,
            password=password,
            namespace="vod-mfc",
        )
        configs = client.get_configs(no_snapshot=True)
        logger.info(f"configs:{configs}")
"""