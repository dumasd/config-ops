from sqlalchemy import create_engine, text
import logging
import json
from sqlfluff import lint, fix

logger = logging.getLogger(__name__)


class TestSqlalchemy:
    def test_selectsql(self):
        conn_string = f"mysql+mysqlconnector://root:12345678@localhost:3306/ms_site"
        engine = create_engine(conn_string)
        with engine.connect() as conn:
            try:
                sql_text = text("select * from tenant")
                result = conn.execute(sql_text)
                if result.returns_rows:
                    columes = result.keys()
                    result_list = [dict(zip(columes, row)) for row in result]
                    logger.info(f"select result: {json.dumps(result_list)}")
                sql_text = text("update tenant set crt_time=0")
                result = conn.execute(sql_text)
                if result.returns_rows:
                    for row in result:
                        logger.info(f"select row: {row}")
            except Exception as ex:
                logger.error(f"Execute sql error {ex}")

    def test_sql_lint(self):
        """
        SQLLint: https://docs.sqlfluff.com/en/stable/reference/rules.html#core-rules
        """

        sql_query = """
        SELECT id, name, age FROM users
        """
        # Lint the SQL query
        lint_result = lint(sql_query.strip(), dialect="mysql")
        # Print the linting results
        for violation in lint_result:
            logger.info(f"vilation: {violation}")
            # print(f"Line: {violation.line_no}, Column: {violation.line_pos}")
            # print(f"Code: {violation.code}, Description: {violation.description}")
