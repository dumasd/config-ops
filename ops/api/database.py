""" 执行SQL操作 """
from flask import Blueprint,request,make_response,jsonify,current_app
import re, logging
from sqlalchemy import create_engine, text
from marshmallow import Schema, fields, ValidationError

logger = logging.getLogger(__name__)

bp = Blueprint('database', __name__)

class RunSqlSchema(Schema):
    db_id = fields.Str(required=True)
    sql = fields.Str(required=True)

def remove_comments(sql_script):
    sql_script = re.sub(r'--.*?\n', '', sql_script)
    sql_script = re.sub(r'/\*.*?\*/', '', sql_script, flags=re.DOTALL)
    return sql_script

def validate_sql(sql_script:str, db_config):
    try:
        url = db_config.get('url')
        engine = create_engine(url)
        sql_script = remove_comments(sql_script)
        sql_commands = sql_script.split(';')
        for sql in sql_commands:
            if sql.strip():
                sql_text = text(sql)
                compiled = sql_text.compile(engine)    
                logger.info(compiled)
    except Exception as e:
        return False,  f"Invalid SQL statement: {str(e)}"

def execute_sql(sql_script, db_config):
    engine = None
    sql_commands = None
    try:
        url = db_config.get('url')
        engine = create_engine(url)
        sql_script = remove_comments(sql_script)
        sql_commands = sql_script.split(';')    
    except Exception as e:
        logger.error(f"Init database or sql error. {e}")
        return False,  f"Init database or sql error: {str(e)}" 
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 执行结果包装一下
            for sql in sql_commands:
                if sql.strip():
                    sql_text = text(sql)
                    logger.info(f'============ 执行SQL语句 =========\n {sql_text}')
                    result = conn.execute(sql_text)
                    logger.info(f"Number of row affected: {result.rowcount}")
                    # for row in result:
                    #     logger.info(row)
            trans.commit()
            return True, "OK"
        except Exception as ex:
            trans.rollback()
            logger.error(f"Execute sql error {ex}")
            return False, f"Execute sql error {ex}"
        finally:
            trans.close()

def get_database_config(db_id):
    configs = current_app.config['database']
    return configs[db_id]
        
@bp.route('/database/v1/run-sql', methods=['POST'])
def run_sql():
    schema = RunSqlSchema()
    data = None
    try:
       data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    print(data)
    
    db_id = data.get('db_id')
    db_config = get_database_config(db_id)        
    if db_config == None:
        return make_response('Database config not found', 404)
    success, result = execute_sql(data.get('sql'), db_config)
    return "OK"
    