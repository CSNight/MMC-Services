import os
import shutil
from subprocess import Popen, PIPE

from flask import jsonify
from pkg_resources import resource_filename

from server_utils.MongoDBOP import MongoDBOP


class GetConfig:
    def __init__(self):
        self.__mongo_admin_server = {'host': '127.0.0.1', 'port': 27017, 'db': 'mmc', 'user': 'administrator',
                                     'pwd': 'qnyh1991'}
        self.__mongo_mmc_server = {'host': '127.0.0.1', 'port': 27017, 'db': 'mmc', 'user': 'mmc', 'pwd': '123456'}
        self.__redis_cache_server = {'host': '127.0.0.1', 'port': 6379, 'db': 0}
        self.__db_dir = 'F:\\BigDataSoftware\MongoDB\\'
        self.__mongo_export_cmd = self.__db_dir + 'bin\\mongodump -h 127.0.0.1 -d mmc -o' + self.__db_dir + 'backup -j 8'
        self.__mongo_restore_cmd = self.__db_dir + 'bin\\mongorestore -h 127.0.0.1 -d mmc --dir ' + self.__db_dir + 'backup\\mmc -j 8 --numInsertionWorkersPerCollection 8'
        self.__mongo_collections_list = [
            'file_store.files',
            'file_store.chunks',
            'video_shortcut.files',
            'video_shortcut.chunks',
            'user_info',
            'user_data_tree',
            'user_view_save',
            'icon',
            'versions'
        ]
        self.res_code = {
            101: 'file_not_found',
            102: 'data_not_found',
            103: 'operation_failed',
            200: 'success',
            300: 'db_error',
            404: 'server_invalid',
            401: 'user_info_incorrect',
            402: 'code_incorrect',
            403: 'user_exist',
            500: 'time_out',
            501: 'not_login',
            502: 'param_none'
        }
        self.tmp_image_dir = resource_filename(__name__, 'resource\\image')
        self.tmp_video_dir = resource_filename(__name__, 'resource\\video')
        self.tmp_audio_dir = resource_filename(__name__, 'resource\\audio')
        self.tmp_docs_dir = resource_filename(__name__, 'resource\\doc')
        self.tmp_package_dir = resource_filename(__name__, 'resource\\package')
        if not os.path.exists(self.tmp_package_dir):
            os.makedirs(self.tmp_package_dir)
        if not os.path.exists(self.tmp_image_dir):
            os.makedirs(self.tmp_image_dir)
        if not os.path.exists(self.tmp_video_dir):
            os.makedirs(self.tmp_video_dir)
        if not os.path.exists(self.tmp_audio_dir):
            os.makedirs(self.tmp_audio_dir)
        if not os.path.exists(self.tmp_docs_dir):
            os.makedirs(self.tmp_docs_dir)

    def release_db_disk(self, logger):
        shutil.rmtree(self.__db_dir + "\\backup", ignore_errors=True)
        continues_res = Popen(self.__mongo_export_cmd, shell=True, stdout=PIPE)
        for i in iter(continues_res.stdout.readline, 'b'):
            logger.warning(str(i, encoding='gbk'))
            if str(i, encoding='gbk') == "":
                break
        admin_mongo = MongoDBOP(**self.__mongo_admin_server)
        for each in self.__mongo_collections_list:
            admin_mongo.db[each].drop()
        admin_mongo.close()
        continues_res = Popen(self.__mongo_restore_cmd, shell=True, stdout=PIPE)
        for i in iter(continues_res.stdout.readline, 'b'):
            logger.warning(str(i, encoding='gbk'))
            if str(i, encoding='gbk') == "":
                break

    def get_tmp_by_type(self, f_type):
        if f_type == 'image':
            return self.tmp_image_dir
        elif f_type == 'video':
            return self.tmp_video_dir
        elif f_type == 'doc':
            return self.tmp_docs_dir
        elif f_type == 'audio':
            return self.tmp_audio_dir
        else:
            return self.tmp_package_dir

    def get_mongo_connection(self):
        return self.__mongo_mmc_server

    def get_redis_connection(self):
        return self.__redis_cache_server

    def clean_tmp_file(self):
        file_list = [(self.tmp_image_dir + '\\' + i) for i in os.listdir(self.tmp_image_dir)]
        file_list.extend([(self.tmp_video_dir + '\\' + i) for i in os.listdir(self.tmp_video_dir)])
        file_list.extend([(self.tmp_docs_dir + '\\' + i) for i in os.listdir(self.tmp_docs_dir)])
        file_list.extend([(self.tmp_audio_dir + '\\' + i) for i in os.listdir(self.tmp_audio_dir)])
        file_list.extend([(self.tmp_package_dir + '\\' + i) for i in os.listdir(self.tmp_package_dir)])
        for each in file_list:
            shutil.rmtree(each, ignore_errors=True)

    def build_response(self, interface=None, element=None, status=None, message=None):
        if message is None:
            return jsonify({
                'ns_type': interface,
                'element': element,
                'status': status,
                'message': self.res_code[status]
            })
        else:
            return jsonify({
                'ns_type': interface,
                'element': element,
                'status': status,
                'message': message
            })
