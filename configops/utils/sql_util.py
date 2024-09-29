from sqlfluff import lint, fix
import logging

logger = logging.getLogger(__name__)


def check_sql(sql, dialect="ansi"):
    # Lint the SQL query
    lint_result = lint(sql, dialect=dialect)
    # Print the linting results
    for violation in lint_result:
        logger.info(f"vilation: {violation}")
        if violation.code and violation.code == "PRS":
            # sql 无法解析
            return False, "SQL syntax error"
    return True, "OK"
