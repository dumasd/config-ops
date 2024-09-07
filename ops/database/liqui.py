from pyliquibase import Pyliquibase
import re, sys
from ops.config import get_liquibase_cfg


class LuquibaseCtx:
    def __init__(self) -> None:
        pass

    def _get_liquibase(self, cfg):
        if cfg:
            return Pyliquibase(
                defaultsFile=cfg["defaults-file"] or None,
                jdbcDriversDir=cfg["jdbc-drivers-dir"] or None,
            )
        else:
            return Pyliquibase()

    def init_liquibase(self, app):
        liquibase_cfg = get_liquibase_cfg(app)
        self.liquibase_cfg = liquibase_cfg

    def execute(self, arguments: str):
        args = tuple(re.split(r"\s+", arguments.strip()))
        liquibase = self._get_liquibase(self.liquibase_cfg)
        liquibase.execute(*args)


ctx = LuquibaseCtx()
