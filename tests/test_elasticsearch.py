import re, logging, os, shlex
from configops.api import elasticsearch

logger = logging.getLogger(__name__)


class TestElasticsearch:

    def test_api(self):
        cfg = {
            "url": "https://elastic.dumasdlocal.com",
            "username": "elastic",
            "password": "Z3KChtE0wl8vR351o627lc9G",
        }
        client = elasticsearch.detect_version_and_create_client(cfg)
        client.transport.perform_request(
            url="/movies/_doc/5",
            method="POST",
            body="""
{
  "title": "The Shawshank Redemption",
  "description": "A banker convicted of uxoricide forms a friendship over a quarter century with a hardened convict, while maintaining his innocence and trying to remain hopeful through simple compassion.",
  "genre": ["Drama"],
  "release_date": "1994-07-16",
  "rating": 9.3,
  "cast": [
    { "name": "Tim Robbins", "role": "Andy Dufresne" },
    { "name": "Morgan Freeman", "role": "Ellis Boyd 'Red' Redding" }
  ],
  "duration": 144,
  "language": "English"
}
                                         """,
            headers={"Content-Type": "application/json"},
        )

        try:
            resp = client.transport.perform_request(
                url="/movies/_search",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            logger.info(f"search resp: {resp}")
        except Exception as e:
            logger.error(f"request error: {e}", exc_info=True)
