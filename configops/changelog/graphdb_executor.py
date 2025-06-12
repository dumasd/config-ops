# -*- coding: utf-8 -*-
# @Author  : Bruce Wu
# @Time    : 2025/06/12 10:21
import logging
import requests
from gremlin_python.driver import client as gremlin_client
import SPARQLWrapper
from configops.utils import secret_util
from configops.utils.exception import ChangeLogException
from configops.utils.constants import GraphdbDialect

logger = logging.getLogger(__name__)

_AWS_NEPTUNEDB_SERVICE_NAME = "neptune-db"


class BaseExecutor:
    def execute_gremlin(self, system_cfg, querys: list, **kwargs):
        raise NotImplementedError("Gremlin script execution is not supported.")

    def execute_opencypher(self, system_cfg, querys: list, **kwargs):
        raise NotImplementedError("OpenCypher script execution is not supported.")

    def execute_sparql(self, system_cfg, querys: list, **kwargs):
        raise NotImplementedError("Sparql script execution is not supported.")


class NeptuneExecutor(BaseExecutor):
    def execute_gremlin(self, system_cfg, querys: list, **kwargs):
        secure = system_cfg.get("secure", False)
        schema = "wss" if secure else "ws"
        host = system_cfg["host"]
        port = system_cfg["port"]
        request_url = f"{schema}://{host}:{port}/gremlin"
        headers = secret_util.get_aws_request_headers(
            system_cfg.get("aws_iam_authentication"),
            "GET",
            _AWS_NEPTUNEDB_SERVICE_NAME,
            request_url,
            None,
        )
        client = gremlin_client.Client(
            url=request_url, traversal_source="g", headers=headers
        )
        try:
            for query in querys:
                parts = query.split(";")
                for part in parts:
                    if part.strip():
                        try:
                            future_result = client.submit_async(part.strip())
                            result = future_result.result().one()
                            logger.info(f"Neptune execute gremlin. result: {result}")
                        except KeyError:
                            pass
        finally:
            client.close()

    def execute_opencypher(self, system_cfg, querys: list, **kwargs):
        secure = system_cfg.get("secure", False)
        schema = "https" if secure else "http"
        host = system_cfg["host"]
        port = system_cfg["port"]
        request_url = f"{schema}://{host}:{port}/openCypher"
        for query in querys:
            parts = query.split(";")
            for part in parts:
                if part.strip():
                    payload = {"query": part}
                    headers = secret_util.get_aws_request_headers(
                        system_cfg.get("aws_iam_authentication"),
                        "POST",
                        _AWS_NEPTUNEDB_SERVICE_NAME,
                        request_url,
                        payload,
                    )
                    response = requests.post(
                        request_url, headers=headers, verify=False, data=payload
                    )
                    logger.info(
                        f"Neptune execute opencypher. status: {response.status_code}, text: {response.text}"
                    )
                    if response.status_code < 200 or response.status_code >= 300:
                        raise ChangeLogException(response.text)

    def execute_sparql(self, system_cfg, querys: list, **kwargs):
        secure = system_cfg.get("secure", False)
        schema = "https" if secure else "http"
        host = system_cfg["host"]
        port = system_cfg["port"]
        request_url = f"{schema}://{host}:{port}/sparql"
        for query in querys:
            headers = secret_util.get_aws_request_headers(
                system_cfg.get("aws_iam_authentication"),
                "POST",
                _AWS_NEPTUNEDB_SERVICE_NAME,
                request_url,
                {"query": query},
            )
            sparql = SPARQLWrapper.SPARQLWrapper(request_url)
            sparql.setMethod(SPARQLWrapper.POST)
            for k, v in headers.items():
                sparql.addCustomHttpHeader(k, v)
            sparql.setQuery(query)
            result = sparql.query()
            logger.info(f"Neptune execute sparql result: {result}")


class Neo4jExecutor(BaseExecutor):
    def execute_opencypher(self, system_cfg, querys: list, **kwargs):
        dataset = kwargs["dataset"]
        secure = system_cfg.get("secure", False)
        schema = "https" if secure else "http"
        host = system_cfg["host"]
        port = system_cfg["port"]
        username = system_cfg.get("username")
        password = secret_util.get_secret_data(system_cfg).password

        request_url = f"{schema}://{host}:{port}/db/{dataset}/tx/commit"
        statements = []
        for query in querys:
            parts = query.split(";")
            for part in parts:
                if part.strip():
                    statements.append({"statement": part.strip()})

        response = requests.post(
            request_url,
            json={"statements": statements},
            auth=requests.auth.HTTPBasicAuth(username=username, password=password),
            allow_redirects=True,
        )
        logger.info(
            f"Neo4j execute openCypher. status: {response.status_code}, text: {response.text}"
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise ChangeLogException(response.text)
        resp_body = response.json()
        errors = resp_body.get("errors")
        if errors and len(errors) > 0:
            notifications = resp_body.get("notifications")
            error_text = ""
            if notifications and len(notifications) > 0:
                error_text = ";".join([item["description"] for item in notifications])
            else:
                error_text = ";".join([item["message"] for item in errors])
            raise ChangeLogException(error_text)


class JenafusekiExecutor(BaseExecutor):
    def execute_sparql(self, system_cfg, querys: list, **kwargs):
        secure = system_cfg.get("secure", False)
        schema = "https" if secure else "http"
        host = system_cfg["host"]
        port = system_cfg["port"]
        username = system_cfg.get("username")
        password = secret_util.get_secret_data(system_cfg).password
        dataset = kwargs["dataset"]

        sparql = SPARQLWrapper.SPARQLWrapper(f"{schema}://{host}:{port}/{dataset}")
        sparql.setHTTPAuth(SPARQLWrapper.BASIC)
        sparql.setCredentials(username, password)
        sparql.setMethod(SPARQLWrapper.POST)
        for query in querys:
            sparql.setQuery(query)
            query_result = sparql.query()
            logger.info(f"Jenafuseki execute sparql. result: {query_result}")


class JanusgraphExecutor(BaseExecutor):
    def execute_gremlin(self, system_cfg, querys: list, **kwargs):
        secure = system_cfg.get("secure", True)
        schema = "wss" if secure else "ws"
        host = system_cfg["host"]
        port = system_cfg["port"]
        username = system_cfg.get("username", "")
        password = secret_util.get_secret_data(system_cfg).password
        request_url = f"{schema}://{host}:{port}/gremlin"
        client = gremlin_client.Client(
            url=request_url,
            traversal_source="g",
            username=username,
            password=password,
        )
        try:
            for query in querys:
                parts = query.split(";")
                for part in parts:
                    if part.strip():
                        try:
                            future_result = client.submit_async(part.strip())
                            future_result.result().one()
                        except KeyError:
                            pass
        finally:
            client.close()


_DIALECT_EXECUTOR_MAP = {
    GraphdbDialect.NEPTUNE.value: NeptuneExecutor(),
    GraphdbDialect.NEO4J.value: Neo4jExecutor(),
    GraphdbDialect.JENAFUSEKI.value: JenafusekiExecutor(),
    GraphdbDialect.JANUSGRAPH.value: JanusgraphExecutor(),
}


def get_executor(dialect: str) -> BaseExecutor:
    return _DIALECT_EXECUTOR_MAP.get(dialect)
