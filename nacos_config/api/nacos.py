from flask import Blueprint, jsonify, make_response, request, current_app
import nacos
import io
import logging
from nacos_config.utils import parser, constants
from ruamel import yaml as ryaml

bp = Blueprint('nacos', __name__)

logger = logging.getLogger(__name__)

""" 获取指定配置 """


""" 修改预览 """
@bp.route('/modify/preview', methods=['POST'])
def modify_preview():
    data = request.get_json()
    nacosConfigs = current_app.config['NACOS_CONFIGS']
    
    nacosId = data.get('nacos_id')
    nacosConfig = nacosConfigs.get(nacosId)
    if nacosConfig == None:
        return make_response('Nacos config not found', 404)
    namespace_id = data.get('namespace_id')
    group = data.get('group')
    data_id = data.get('data_id')
    patch_content = data.get('patch_content')
    full_content = data.get('full_content')
    
    print(data, nacosConfig)
    # 目前只支持yaml、properties、json 配置
    
    # 1. 从nacos捞当前配置
    client = nacos.NacosClient(server_addresses=nacosConfig.get('url'),
                               username=nacosConfig.get('username'),
                               password=nacosConfig.get('password'),
                               namespace=namespace_id)
    current_content = client.get_config(data_id=data_id,group=group)
    print(current_content)
    
    format, parser_obj, yaml = parser.parse_content(current_content)
    
    print(format, parser_obj)
    
    if format == constants.YAML:
        logger.info("modify yaml")
        parser_obj['foo'] = "fdaff"
        output_stream = io.StringIO()
        yaml.dump(parser_obj, output_stream)
        for k, v in parser_obj.items():
            print(k, v)
    elif format == constants.PROPERTIES:
        logger.info("modify properties")
        
    else:
        return make_response('Unsupported content format', 400)            
        
    
    
    
    # 2. 解析full_content，比对当前配置，新增或删除
    
    # 3. 解析patch_content，比对新增或删除
    
    return "OK"

    
""" 修改配置 """



    