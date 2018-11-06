import time
import uuid
from io import BytesIO

from flask import Blueprint, request, session, make_response

from encrypt_utils import EncryptUtils
from config import GetConfig
from server_utils.MongoDBOP import MongoDBOP
from server_utils.VerifyCoder import VerifyCoder


class UserOperation:
    def __init__(self):
        self.__mongo = MongoDBOP(**config.get_mongo_connection())
        self.__collection = "user_info"
        self.__timeout = 3600
        self.__online_users = {}
        self.__encrypt = EncryptUtils()
        self.__pwd = "mmc_key_ser"

    def get_user_info(self, uid):
        for key in self.__online_users.keys():
            if uid == key:
                username = self.__online_users[key]['username']
                res = self.__mongo.search_by_kv_pair(self.__collection, {'username': username})
                if len(res) > 0:
                    return res[0]
        return None

    def get_user_status(self, uid):
        if self.__online_users.__contains__(uid):
            if time.time() - self.__online_users[uid]['login_time'] > self.__timeout:
                del self.__online_users[uid]
                if session.__contains__(uid):
                    session.pop(uid)
                return config.build_response('check_status', '', 500)
            else:
                return config.build_response('check_status', '', 200)
        else:
            return config.build_response('check_status', '', 501)

    def user_login(self, username, pwd, code):
        if username != '' and pwd != '' and code != "":
            if str(session.get("code")) != code.upper():
                return config.build_response('login', '', 402)
            else:
                for uid in self.__online_users.keys():
                    if username == self.__online_users[uid]['username']:
                        return config.build_response('login', {'role': self.__online_users[uid]['role'], 'uid': uid},
                                                     200)
                pwd_en = self.__encrypt.encrypt_str(pwd, self.__pwd, "aes")
                res = self.__mongo.search_by_kv_pair(self.__collection, {'username': username, 'pwd': pwd_en})
                if len(res) == 0:
                    return config.build_response('login', '', 401)
                else:
                    uid = str(uuid.uuid4())
                    self.__online_users[uid] = session[uid] = {
                        'username': username,
                        'role': res[0]['role'],
                        'login_time': time.time()
                    }
                    return config.build_response('login', {'role': res[0]['role'], 'uid': uid}, 200)
        else:
            return config.build_response('login', '', 502)

    def user_logout(self, uid):
        if self.__online_users.__contains__(uid):
            del self.__online_users[uid]
            if session.__contains__(uid):
                session.pop(uid)
            return config.build_response('logout', '', 200)
        else:
            return config.build_response('logout', '', 501)

    def sign_up(self, role, username, pwd):
        if username != '' and pwd != '' and role != '':
            res_user = self.__mongo.search_by_kv_pair(self.__collection, [{'username': username}, {'role': role}],
                                                      logic_type='or')
            if len(res_user) > 0:
                return config.build_response('sign_up', '', 403)
            uid = str(uuid.uuid4())
            user_data = {
                'uid': uid,
                'role': role,
                'username': username,
                'pwd': self.__encrypt.encrypt_str(pwd, self.__pwd, "aes")
            }
            res = self.__mongo.insert(self.__collection, user_data)
            uid = str(uuid.uuid4())
            if res is not None:
                self.__online_users[uid] = session[uid] = {
                    'username': username,
                    'role': role,
                    'login_time': time.time()
                }
                return config.build_response('sign_up', {'role': role, 'uid': uid}, 200)
            else:
                return config.build_response('sign_up', '', 300)
        else:
            return config.build_response('sign_up', '', 502)


config = GetConfig()
uo = UserOperation()
user = Blueprint('user', __name__)


@user.route('/sign_up', methods=['GET'])
def sign_up():
    role = request.args.get('role')
    username = request.args.get('username')
    pwd = request.args.get('pwd')
    if username and role and pwd:
        return uo.sign_up(role, username, pwd)
    else:
        return config.build_response('sign_up', '', 502)


@user.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        username = request.args.get('username')
        password = request.args.get('pwd')
        code = request.args.get('code')
    else:
        username = request.form["username"]
        password = request.form["pwd"]
        code = request.form["code"]
    if username and password and code:
        return uo.user_login(username, password, code)
    else:
        return config.build_response('login', '', 502)


@user.route('/check_login', methods=['GET'])
def check_login():
    uid = request.args.get('uid')
    if uid is None:
        return config.build_response('check_status', '', 502)
    else:
        return uo.get_user_status(uid)


@user.route('/logout', methods=['GET'])
def logout():
    uid = request.args.get('uid')
    if uid is None:
        return config.build_response('logout', '', 502)
    else:
        return uo.user_logout(uid)


@user.route('/verify', methods=['GET'])
def verify_code():
    w = request.args.get('w')
    h = request.args.get('h')
    if w and h:
        img_code, img = VerifyCoder().output_image(int(w), int(h), 4)
    else:
        return ""
    buf = BytesIO()
    img.save(buf, 'jpeg')
    buf_str = buf.getvalue()
    session["code"] = img_code
    session.permanent = True
    response = make_response(buf_str)
    response.headers['Content-Type'] = 'image/jpeg'
    return response
