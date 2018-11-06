import gc
import mimetypes
import os
import threading
import uuid
from subprocess import Popen, SubprocessError, CalledProcessError, PIPE

from bson import ObjectId
from flask import Blueprint, request, make_response
from mutagen import File
from pkg_resources import resource_filename

from config import GetConfig
from server_utils.MongoDBOP import MongoDBOP
from user_manage.user_views import uo


class FileOperation:
    def __init__(self):
        self.fpg_video_trans = resource_filename(__name__, "ffmpeg.exe") + " -i {0} -c:v copy -c:a copy {1}"
        self.fpg_audio_trans = resource_filename(__name__, "ffmpeg.exe") + " -i {0} -c:a copy {1}"
        self.fag_video_shortcut = resource_filename(__name__,
                                                    "ffmpeg.exe") + " -i {0} -y -f image2 -ss 30 -s 150x80 {1}"
        self.__mongo = MongoDBOP(**config.get_mongo_connection())
        self.__file_set = "file_store"
        self.__short_cut = "video_shortcut"
        self.__collection = "user_data_tree"

    def cache_file(self, fid, f_type):
        if self.__mongo.check_file(self.__file_set, fid):
            res = self.__mongo.search_by_kv_pair(self.__file_set + '.files', {'_id': ObjectId(fid)})
            for dirs in os.listdir(config.get_tmp_by_type(f_type) + '\\'):
                if os.path.exists(config.get_tmp_by_type(f_type) + '\\' + dirs + '\\' + res[0]['file_name']):
                    return config.build_response("cache_file", {'name': res[0]['file_name'], "chd": dirs}, 200)
            chd = str(uuid.uuid4())
            tmp_path = config.get_tmp_by_type(f_type) + '\\' + chd + '\\'
            os.makedirs(tmp_path)
            db_file = self.__mongo.get_file(self.__file_set, fid)
            fn = db_file._file['file_name']
            tmp_file = tmp_path + fn
            with open(tmp_file, 'wb') as f:
                f.write(db_file.read())
                f.flush()
            del db_file
            gc.collect()
            return config.build_response("cache_file", {'name': fn, "chd": chd}, 200)
        else:
            return config.build_response("cache_file", '', 101)

    def get_tmp_file(self, fid):
        if self.__mongo.check_file(self.__file_set, fid):
            db_file = self.__mongo.get_file(self.__file_set, fid)
            mime_type = mimetypes.guess_type(db_file._file['file_name'])[0]
            response = make_response(db_file.read())
            response.headers['Content-Type'] = mime_type
            response.headers['Content-Disposition'] = 'attachment; filename={}'.format(
                db_file._file['file_name'].encode().decode('latin-1'))
            del db_file
            return response
        else:
            return config.build_response("download", '', 101)

    def media_format_transform(self, file_path, f_type):
        try:
            new_path = file_path
            command = ""
            ext = os.path.splitext(file_path)[1].lower()
            if f_type == "video":
                new_path = file_path.replace(ext, '.mp4')
                command = self.fpg_video_trans.format(file_path, new_path)
            elif f_type == 'audio':
                new_path = file_path.replace(ext, '.mp3')
                command = self.fpg_video_trans.format(file_path, new_path)
            continues_res = Popen(command, shell=False, stdout=PIPE)
            for i in iter(continues_res.stdout.readline, 'b'):
                if str(i, encoding='gbk') == "":
                    break
            return new_path
        except SubprocessError or CalledProcessError:
            return None

    def media_shortcut(self, file_path):
        try:
            new_path = os.path.dirname(file_path) + "\\" + str(uuid.uuid4()) + ".jpg"
            command = self.fag_video_shortcut.format(file_path, new_path)
            continues_res = Popen(command, shell=False, stdout=PIPE)
            for i in iter(continues_res.stdout.readline, 'b'):
                if str(i, encoding='gbk') == "":
                    break
            obj_id = self.__mongo.insert_singlefile_by_path(self.__short_cut, new_path,
                                                            {'belongs': os.path.split(file_path)[1]})
            if obj_id:
                os.remove(new_path)
            return obj_id
        except IOError or SubprocessError or CalledProcessError:
            return ""

    def media_info_extract(self, f_path):
        _MEDIA_INFO = {
            "title": "UNKNOWN",
            "artist": "UNKNOWN",
            "album": "UNKNOWN",
            "shortcut": "UNKNOWN",
            "bitrate": "UNKNOWN"
        }
        media_info = File(f_path)
        if media_info.tags is not None:
            if media_info.tags.__contains__("APIC:"):
                preview = media_info.tags["APIC:"].data
                tmp = config.get_tmp_by_type("image") + "short.jpg"
                with open(tmp, "wb") as img:
                    img.write(preview)
                obj_id = self.__mongo.insert_singlefile_by_path(self.__short_cut, tmp,
                                                                {"belongs": os.path.split(f_path)[1]})
                if obj_id:
                    os.remove(tmp)
                _MEDIA_INFO["shortcut"] = obj_id if obj_id else ""
            if media_info.tags.__contains__("T1T2"):
                _MEDIA_INFO["title"] = media_info.tags["T1T2"].text[0].replace(" ", "")
            if media_info.tags.__contains__("TPE1"):
                _MEDIA_INFO["artist"] = media_info.tags["TPE1"].text[0].replace(" ", "")
            if media_info.tags.__contains__("TALB"):
                _MEDIA_INFO["album"] = media_info.tags["TALB"].text[0].replace(" ", "")
        if media_info.info is not None:
            if hasattr(media_info.info, "bitrate"):
                _MEDIA_INFO["bitrate"] = media_info.info.bitrate
        MEDIA_INFO = {
            "title": _MEDIA_INFO["title"] if _MEDIA_INFO["title"] != "" else "UNKNOWN",
            "artist": _MEDIA_INFO["artist"] if _MEDIA_INFO["artist"] != "" else "UNKNOWN",
            "album": _MEDIA_INFO["album"] if _MEDIA_INFO["album"] != "" else "UNKNOWN",
            "shortcut": _MEDIA_INFO["shortcut"] if _MEDIA_INFO["shortcut"] != "" else "UNKNOWN",
            "bitrate": _MEDIA_INFO["bitrate"] if _MEDIA_INFO["bitrate"] != "" else "UNKNOWN",
            "lyric": 0
        }
        return MEDIA_INFO

    def after_upload_process(self, f_type, uni_id, is_trans):
        res = []
        tmp_path = config.get_tmp_by_type(f_type) + "\\" + uni_id + "\\"
        file_list = [(tmp_path + i) for i in os.listdir(tmp_path)]
        for tp in file_list:
            tmp = tp
            info = {}
            trans_status = False
            if is_trans == "true" and (f_type == "audio" or f_type == "video") and os.path.splitext(tp)[1] != '.mp3' and \
                    os.path.splitext(tp)[1] != '.mp4'and os.path.splitext(tp)[1] != '.jpg':
                tmp = self.media_format_transform(tp, f_type)
                if tmp != tp:
                    trans_status = True
                    os.remove(tp)
            if f_type == 'video':
                obj_id = self.media_shortcut(tmp)
                info = {'shortcut': obj_id if obj_id else ''}
            if f_type == 'audio':
                info = self.media_info_extract(tmp)
            res.append({'file_path': tmp, 'des': info, "trans_status": trans_status})
        return config.build_response('after_upload', res, 200)


config = GetConfig()
fo = FileOperation()
file = Blueprint('file', __name__)
globalLock = threading.Lock()


@file.route('/upload', methods=['POST'])
def file_upload():
    if request.method == 'POST':
        if request.form["name"] and request.form['f_type'] and request.form['unique_id']:
            tmp_dir = config.get_tmp_by_type(request.form['f_type']) + '\\' + request.form['unique_id']
            globalLock.acquire()
            if not os.path.exists(tmp_dir):
                os.mkdir(tmp_dir)
            globalLock.release()
            file_dir = tmp_dir + '\\' + request.form["name"]
            try:
                with open(file_dir, "ab+") as f:
                    f.write(bytes(request.files['file'].read()))
                    f.flush()
                gc.collect()
            except IOError or SystemError:
                pass
            return config.build_response('upload', '', 200)
        else:
            return config.build_response('upload', '', 404)
    else:
        return config.build_response('upload', '', 404)


@file.route('after_upload', methods=['GET'])
def after_upload():
    f_type = request.args.get('f_type')
    is_trans = request.args.get('is_trans')
    uni_id = request.args.get('unique_id')
    if f_type and is_trans and uni_id:
        return fo.after_upload_process(f_type, uni_id, is_trans)
    else:
        return config.build_response('after_upload', '', 502)


@file.route('download', methods=['GET'])
def file_download():
    uid = request.args.get('uid')
    fid = request.args.get('fid')
    if uid and fid:
        data = uo.get_user_info(uid)
        if data:
            return fo.get_tmp_file(fid)
        else:
            return config.build_response('download', '', 501)
    else:
        return config.build_response('download', '', 502)


@file.route('cache_file', methods=['GET'])
def cache_to_file():
    uid = request.args.get('uid')
    fid = request.args.get('fid')
    f_type = request.args.get('f_type')
    if uid and fid and f_type:
        data = uo.get_user_info(uid)
        if data:
            return fo.cache_file(fid, f_type)
        else:
            return config.build_response('cache_file', '', 501)
    else:
        return config.build_response('cache_file', '', 502)
