import nacos
import logging
import json

logger = logging.getLogger(__name__)


class ConfigOpsNacosClient(nacos.NacosClient):

    def list_namespace(self, timeout=None):
        try:
            resp = self._do_sync_req(
                url="/nacos/v1/console/namespaces",
                timeout=(timeout or self.default_timeout),
            )
            c = resp.read()
            response_data = json.loads(c.decode("UTF-8"))
            return response_data
        except Exception as e:
            logger.exception("[list-namespace] exception %s occur" % str(e))
            raise
