# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import abc
import logging
from logging.handlers import TimedRotatingFileHandler
import logging.handlers

import flask.app
import flask.config

logger = logging.getLogger(__name__)


class LoggingConfigurator(abc.ABC):  # pylint: disable=too-few-public-methods
    @abc.abstractmethod
    def configure_logging(
        self, app_config: flask.config.Config, debug_mode: bool
    ) -> None:
        pass


class DefaultLoggingConfigurator(  # pylint: disable=too-few-public-methods
    LoggingConfigurator
):
    def configure_default(self) -> None:
        logging.basicConfig(format="[%(asctime)s] %(levelname)s %(name)s %(message)s")
        logging.getLogger().setLevel(logging.INFO)

    def configure_logging(
        self, app_config: flask.config.Config, debug_mode: bool
    ) -> None:
        log_conf = app_config.get("logging", {})
        level = log_conf.get("level", "INFO")
        format = log_conf.get(
            "format", "[%(asctime)s] %(levelname)s %(name)s %(message)s"
        )
        logging.basicConfig(format=format)
        logging.getLogger().setLevel(level)

        # if app_config["ENABLE_TIME_ROTATE"]:
        #     logging.getLogger().setLevel(app_config["TIME_ROTATE_LOG_LEVEL"])
        #     handler = TimedRotatingFileHandler(
        #         app_config["FILENAME"],
        #         when=app_config["ROLLOVER"],
        #         interval=app_config["INTERVAL"],
        #         backupCount=app_config["BACKUP_COUNT"],
        #     )
        #     logging.getLogger().addHandler(handler)

        logger.info("logging was configured successfully")
