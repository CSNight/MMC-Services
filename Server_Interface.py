import os
from argparse import ArgumentParser
from datetime import timedelta
from logging import Logger, Formatter, WARN
from logging.handlers import RotatingFileHandler

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import request, Flask, send_from_directory, render_template
from flask_cors import CORS

from config import GetConfig
from data_manage.file_upload import file
from data_manage.tree_manage import tree
from data_views.file_transform import trans
from data_views.player_logic import logic
from user_manage.user_views import user

# Instantiate the Node
app = Flask(__name__)
CORS(app=app, supports_credentials=True)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.permanent_session_lifetime = timedelta(hours=1)
app.register_blueprint(user, url_prefix='/user')
app.register_blueprint(file, url_prefix='/file')
app.register_blueprint(tree, url_prefix='/tree')
app.register_blueprint(trans, url_prefix='/trans')
app.register_blueprint(logic, url_prefix='/logic')

logger = Logger(__name__)
logger.setLevel(WARN)
f_handler = RotatingFileHandler(filename="logs/mmc_server.log", maxBytes=2048 * 1024, backupCount=3, encoding='utf-8')
f_handler.setFormatter(Formatter("%(asctime)s  %(filename)s : %(levelname)s  %(message)s"))
logger.addHandler(f_handler)


@app.before_request
def before_log():
    if request.method == "GET":
        logger.debug(
            'Request--> method:{0} url:{1} params:{2}'.format(request.method, request.url,
                                                              str(request.query_string, encoding='utf-8')))
    else:
        logger.debug(
            'Request--> method:{0} url:{1} params:{2}'.format(request.method, request.url, str(request.form.to_dict())))


@app.after_request
def after_log(response):
    if response.mimetype == 'text/html' or response.mimetype == 'application/xml':
        logger.debug('Response--> rendering template status %s', response.status)
    elif response.mimetype == "image/x-icon":
        logger.debug('Response--> return a favicon.ico %s', response.status)
    elif response.mimetype == 'image/jpeg':
        logger.debug('Response--> return a image status %s', response.status)
    elif response.mimetype == 'application/json':
        logger.debug('Response--> content:%s status %s' % (
            str(response.data, encoding='utf-8').replace('\n', '').replace(' ', ''), response.status))
    else:
        logger.debug('Response--> download file status %s', response.status)
    return response


@app.errorhandler(500)
def internal_error_handler(error):
    logger.exception(str(error))


@app.errorhandler(404)
def un_exists_error_handler(error):
    logger.exception(str(error))


@app.route('/', methods=['GET', 'POST'])
def index():
    base_url = request.base_url + "API"
    return render_template('index.html', url=request.base_url, api=base_url)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')


@app.route('/API', methods=['GET', 'POST'])
def api_index():
    interfaces = {}
    for inter in app.blueprints.keys():
        resources = []
        for rule in app.url_map.iter_rules():
            if str(rule.rule).startswith('/' + inter):
                options = {}
                paras = []
                for arg in rule.arguments:
                    options[arg] = "[{0}]".format(arg)
                    paras.append(arg)
                resources.append({
                    "methods": ','.join(rule.methods),
                    "url": rule.rule,
                    "paras": paras,
                    "func": rule.endpoint,
                    "response_type": ['application/json']
                })
        interfaces[inter] = resources
    return render_template("API.html", base=request.host_url, interfaces=interfaces), {
        'Content-Type': 'application/xml'}


@app.route('/shutdown', methods=['GET'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


def start_server():
    if __name__ == '__main__':
        parser = ArgumentParser()
        parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
        args = parser.parse_args()
        port = args.port
        app.run('127.0.0.1', port, threaded=True, processes=4)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def clear_dir():
    conf = GetConfig()
    conf.clean_tmp_file()


def db_release():
    requests.request('GET', 'http://127.0.0.1:5000/shutdown')
    conf = GetConfig()
    conf.release_db_disk(logger)
    start_server()


back_task = BackgroundScheduler()
back_task.add_job(clear_dir, 'cron', hour=0, minute=0, second=0)
back_task.add_job(db_release, 'cron', day_of_week=6, hour=0, minute=5, second=0)
back_task.start()

if __name__ == '__main__':
    start_server()
