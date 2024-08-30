import nacos
import logging
import json
from nacos import NacosException
from nacos.client import process_common_config_params, truncate

try:
    # python3.6
    from http import HTTPStatus
    from urllib.request import (
        Request,
        urlopen,
        ProxyHandler,
        HTTPSHandler,
        build_opener,
    )
    from urllib.parse import urlencode, unquote_plus, quote
    from urllib.error import HTTPError, URLError
except ImportError:
    # python2.7
    import httplib as HTTPStatus
    from urllib2 import (
        Request,
        urlopen,
        HTTPError,
        URLError,
        ProxyHandler,
        HTTPSHandler,
        build_opener,
    )
    from urllib import urlencode, unquote_plus, quote

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
    
    def get_config_detail(self, data_id, group):
        configs = self.get_configs(no_snapshot=True, group=group)
        pageItems = configs.get("pageItems")
        for item in pageItems:
            if item.get("dataId") == data_id:
                return item
        return None

    def publish_config_post(
        self, data_id, group, content, app_name=None, config_type=None, timeout=None
    ):
        if content is None:
            raise NacosException("Can not publish none content, use remove instead.")

        data_id, group = process_common_config_params(data_id, group)
        if type(content) == bytes:
            content = content.decode("UTF-8")

        logger.info(
            "[publish] data_id:%s, group:%s, namespace:%s, content:%s, timeout:%s"
            % (data_id, group, self.namespace, truncate(content), timeout)
        )

        data = {
            "dataId": data_id,
            "group": group,
            "content": content.encode("UTF-8"),
        }

        if self.namespace:
            data["tenant"] = self.namespace

        if app_name:
            data["appName"] = app_name

        if config_type:
            data["type"] = config_type

        try:
            resp = self._do_sync_req(
                "/nacos/v1/cs/configs",
                None,
                None,
                data,
                timeout or self.default_timeout,
                "POST",
            )
            c = resp.read()
            logger.info(
                "[publish] publish content, group:%s, data_id:%s, server response:%s"
                % (group, data_id, c)
            )
            return c == b"true"
        except HTTPError as e:
            if e.code == HTTPStatus.FORBIDDEN:
                logger.info(
                    "[publish] publish content fail result code :403, group:%s, data_id:%s"
                    % (group, data_id)
                )
                raise NacosException("Insufficient privilege.")
            else:
                raise NacosException("Request Error, code is %s" % e.code)
        except Exception as e:
            logger.exception("[publish] exception %s occur" % str(e))
            raise
