import json
import os
import shutil
import time
from uuid import uuid4

from flask import Flask, Response, g

name = 'jjwxc_font_tables'
__version__ = '0.1.0'


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=str(uuid4()),
        SQLALCHEMY_DATABASE_URI='sqlite:///{}'.format(os.path.join(app.instance_path, 'jjwxc.sqlite')),
        COORD_TABLE_PATH=os.path.join(app.instance_path, 'coorTable.json'),
        SOURCE_HAN_SANS_SC_NORMAL_PATH=os.path.join(app.root_path, 'font_parser/assets/SourceHanSansSC-Normal.otf'),
        SOURCE_HAN_SANS_SC_REGULAR_PATH=os.path.join(app.root_path, 'font_parser/assets/SourceHanSansSC-Regular.otf'),
        ENABLE_TOOLS=os.getenv('ENABLE_TOOLS', False) and True,
        SOURCE_HAN_SANS_SC_NORMAL_NPZ_PATH=os.path.join(app.instance_path, 'SourceHanSansSC-Normal.npz'),
        SOURCE_HAN_SANS_SC_REGULARL_NPZ_PATH=os.path.join(app.instance_path, 'SourceHanSansSC-Regular.npz'),
        SOURCE_HAN_SANS_SC_NORMAL_JSON_PATH=os.path.join(app.instance_path, 'SourceHanSansSC-Normal.json'),
        SOURCE_HAN_SANS_SC_REGULARL_JSON_PATH=os.path.join(app.instance_path, 'SourceHanSansSC-Regular.json'),
        CACHE_DIR=os.path.join(app.instance_path, 'cache-dir')
    )
    app.logger.info('ENABLE_TOOLS: {}'.format(app.config.get('ENABLE_TOOLS')))

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    with app.app_context():
        init(app)

        from . import healthcheck
        app.register_blueprint(healthcheck.bp)

        from . import index
        app.register_blueprint(index.bp)

        from . import api
        app.register_blueprint(api.bp)

        from . import html
        app.register_blueprint(html.bp)

        from . import font_parser
        font_parser.init_app(app)

        if app.config.get('ENABLE_TOOLS'):
            from . import tools
            app.register_blueprint(tools.bp)
            tools.init_app(app)

    return app


def merge_and_deduplicate_coor_table(app: Flask):
    """将远程 coorTable 合并至本地"""
    with open(app.config.get('COORD_TABLE_PATH'), 'r') as f:
        _local_coorTable = json.load(f)
        local_coor_table = sorted(_local_coorTable, key=lambda x: x[0])
    with open(os.path.join(app.root_path, 'font_parser/assets/coorTable.json'), 'r') as f:
        _remote_coorTable = json.load(f)
        remote_coor_able: list[
            tuple[
                str,
                list[tuple[int, int]]
            ]
        ] = sorted(_remote_coorTable, key=lambda x: x[0])

    from .lib import merge_coor_table, deduplicate_coor_table
    new_local_coor_table = merge_coor_table(remote_coor_able, local_coor_table)
    new_local_coor_table = deduplicate_coor_table(new_local_coor_table)

    if len(new_local_coor_table) != len(local_coor_table):
        if len(new_local_coor_table) != len(local_coor_table):
            with open(app.config.get('COORD_TABLE_PATH'), 'w') as f:
                json.dump(new_local_coor_table, f)


def init(app: Flask):
    # 创建 instance 目录
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    # 初始化数据库
    from . import db
    db.init_app(app)

    if not os.path.exists(app.config.get('CACHE_DIR')):
        os.makedirs(app.config.get('CACHE_DIR'))

    from .cache import cache
    cache.init_app(app, config={"CACHE_TYPE": "FileSystemCache", "CACHE_DIR": app.config.get('CACHE_DIR'),
                                "CACHE_DEFAULT_TIMEOUT": 86400})

    if not os.path.exists(os.path.join(app.instance_path, 'jjwxc.sqlite')):
        db.init_db()

    # 复制/合并 coorTable.json
    if not os.path.exists(app.config.get('COORD_TABLE_PATH')):
        shutil.copy(
            os.path.join(app.root_path, 'font_parser/assets/coorTable.json'),
            app.config.get('COORD_TABLE_PATH')
        )
    else:
        try:
            merge_and_deduplicate_coor_table(app)
        except json.decoder.JSONDecodeError:
            shutil.copy(
                os.path.join(app.root_path, 'font_parser/assets/coorTable.json'),
                app.config.get('COORD_TABLE_PATH')
            )

    @app.before_request
    def before_request():
        g.start_time = time.perf_counter()
        g.slow_match_time = 0

    @app.after_request
    def after_request(response: Response):
        response.headers.add('Referrer-Policy', 'same-origin')

        total_time = time.perf_counter() - g.start_time
        time_in_ms = round(total_time * 1000, 6)
        response.headers.add('X-Runtime', time_in_ms)
        response.headers.add('X-Request-Id', str(uuid4()))

        if g.slow_match_time != 0:
            response.headers.add('X-Match-Times', g.slow_match_time)

        return response
