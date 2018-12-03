import json
import time

import redis
from bson import ObjectId
from flask import Blueprint, request

from config import GetConfig
from data_views.lyric_spider import LyricSpider
from server_utils.MongoDBOP import MongoDBOP
from user_manage.user_views import uo


class PlayerLogic:
    def __init__(self):
        self.__mongo = MongoDBOP(**config.get_mongo_connection())
        self.__redis = redis.Redis(**config.get_redis_connection())
        self.__collection = "user_view_save"
        self.__file_store = "file_store.files"
        self.ls = LyricSpider(self.__mongo)
        self.views = {
            'uid': '',
            'favorite': [],
            'custom': [],
            'recent': [],
            'mov_love': []
        }

    @staticmethod
    def __remove_oid(target):
        if dict(target).__contains__("_id"):
            del target["_id"]
        return target

    def create_user_views(self, uid):
        if not self.__mongo.exist(self.__collection, {'uid': uid}):
            new_views = self.views.copy()
            new_views['uid'] = uid
            self.__mongo.insert(self.__collection, new_views)
            return config.build_response('create_views', '', 200)
        else:
            return config.build_response('create_views', 'already_exist', 200)

    def get_user_views(self, uid):
        if self.__mongo.exist(self.__collection, {'uid': uid}):
            res = self.__mongo.search_by_kv_pair(self.__collection, {'uid': uid})
            elements = {
                'favorite': self.get_file_info(res[0]['favorite']),
                'custom': self.get_file_info(res[0]['custom']),
                'mov_love': self.get_file_info(res[0]['mov_love']),
                'recent': []
            }
            recent = self._update_recent(uid, res[0]['recent'])
            for each in recent:
                if self.__mongo.exist(self.__file_store, {'_id': ObjectId(each['fid'])}):
                    _f = self.__mongo.search_by_kv_pair(self.__file_store, {'_id': ObjectId(each['fid'])})
                    if len(_f) > 0:
                        tmp = self.__remove_oid(_f[0])
                        tmp['fid'] = each['fid']
                        elements['recent'].append({'info': tmp, 'time': self._cal_time(each['time'])})
            return config.build_response('get_views', elements, 200)
        else:
            return config.build_response('get_views', '', 102)

    def modify_user_views(self, uid, op_type, col, ids):
        if self.__mongo.exist(self.__collection, {'uid': uid}):
            res = self.__mongo.search_by_kv_pair(self.__collection, {'uid': uid})
            if col != 'recent':
                item_set = list(self._modify_set(op_type, set(res[0][col]), ids))
                self.__mongo.update(self.__collection, {'uid': uid}, '$set', {col: item_set})
            else:
                recent = self._modify_recent(op_type, res[0][col], ids)
                self.__mongo.update(self.__collection, {'uid': uid}, '$set', {col: recent})
            return config.build_response('modify_views', '', 200)
        else:
            return config.build_response('modify_views', '', 102)

    def cache_list(self, uid, m_type, ids):
        if self.__redis.exists(uid + '_' + m_type):
            self.__redis.delete(uid + '_' + m_type)
        self.__redis.sadd(uid + '_' + m_type, *ids)
        if self.__mongo.exist(self.__collection, {'uid': uid}):
            res = self.__mongo.search_by_kv_pair(self.__collection, {'uid': uid})
            recent = self._modify_recent('add', res[0]['recent'], ids)
            self.__mongo.update(self.__collection, {'uid': uid}, '$set', {'recent': recent})
        return config.build_response('cache_list', '', 200)

    def get_cache_list(self, uid, m_type):
        if self.__redis.exists(uid + '_' + m_type):
            res = []
            ss = list(self.__redis.smembers(uid + '_' + m_type))
            play_list = list(map(lambda x: str(x, encoding='utf-8'), ss))
            for item in play_list:
                m_f = self.__mongo.search_by_kv_pair(self.__file_store, {'_id': ObjectId(item)})
                if len(m_f) > 0:
                    tmp = self.__remove_oid(m_f[0])
                    tmp['fid'] = item
                    res.append(tmp)
            return config.build_response('get_list', res, 200)
        else:
            return config.build_response('get_list', [], 102)

    @staticmethod
    def _modify_set(op_type, items, ids):
        if op_type == 'add':
            for each in ids:
                items.add(each)
        elif op_type == 'delete':
            for each in ids:
                if items.__contains__(each):
                    items.remove(each)
        return items

    @staticmethod
    def _modify_recent(op_type, recent, ids):
        if op_type == 'add':
            new_ids = ids.copy()
            for fid in ids:
                for each in recent:
                    if each['fid'] == fid:
                        each['time'] = time.time()
                        new_ids.remove(fid)
            for fid in new_ids:
                recent.append({'fid': fid, 'time': time.time()})
            return recent
        elif op_type == 'delete':
            new_recent = recent.copy()
            for each in recent:
                for fid in ids:
                    if each['fid'] == fid:
                        new_recent.remove(each)
            return new_recent
        else:
            return recent

    @staticmethod
    def _cal_time(cur_time):
        if time.time() - cur_time < 24 * 3600:
            return 0
        elif 24 * 3600 < time.time() - cur_time < 7 * 24 * 3600:
            index = (time.time() - cur_time) // (24 * 3600)
            return index
        elif 7 * 24 * 3600 < time.time() - cur_time < 31 * 24 * 3600:
            return 7
        else:
            return 8

    def _update_recent(self, uid, recent):
        recent_bak = recent.copy()
        for each in recent:
            if time.time() - each['time'] > 30 * 24 * 3600:
                recent_bak.remove(each)
        if len(recent_bak) > 0:
            self.__mongo.update(self.__collection, {'uid': uid}, '$set', {'recent': recent_bak})
        return recent_bak

    def get_file_info(self, file_ids):
        res = []
        for each in file_ids:
            if self.__mongo.exist(self.__file_store, {'_id': ObjectId(each)}):
                _f = self.__mongo.search_by_kv_pair(self.__file_store, {'_id': ObjectId(each)})
                if len(_f) > 0:
                    tmp = self.__remove_oid(_f[0])
                    tmp['fid'] = each
                    res.append(tmp)
        return res


config = GetConfig()
pl = PlayerLogic()

logic = Blueprint('logic', __name__)


@logic.route('/create_views', methods=['GET'])
def get_views():
    uid = request.args.get('uid')
    if uid:
        data = uo.get_user_info(uid)
        if data:
            return pl.create_user_views(data["uid"])
        else:
            return config.build_response('create_views', '', 501)
    else:
        return config.build_response('create_views', '', 502)


@logic.route('/get_views', methods=['GET'])
def get_us_views():
    uid = request.args.get('uid')
    if uid:
        data = uo.get_user_info(uid)
        if data:
            return pl.get_user_views(data["uid"])
        else:
            return config.build_response('get_views', '', 501)
    else:
        return config.build_response('get_views', '', 502)


@logic.route('/modify_views', methods=['POST'])
def modify_views():
    uid = request.form['uid']
    op_type = request.form['op_type']
    col = request.form['col']
    ids = request.form['ids']
    if uid and op_type and col and ids:
        data = uo.get_user_info(uid)
        if data:
            return pl.modify_user_views(data["uid"], op_type, col, json.loads(ids))
        else:
            return config.build_response('modify_views', '', 501)
    else:
        return config.build_response('modify_views', '', 502)


@logic.route('/cache_list', methods=['POST'])
def cache_lists():
    uid = request.form['uid']
    m_type = request.form['m_type']
    ids = request.form['ids']
    if uid and ids and m_type:
        data = uo.get_user_info(uid)
        if data:
            return pl.cache_list(data["uid"], m_type, json.loads(ids))
        else:
            return config.build_response('cache_list', '', 501)
    else:
        return config.build_response('cache_list', '', 502)


@logic.route('/get_list', methods=['POST'])
def get_list():
    uid = request.form['uid']
    m_type = request.form['m_type']
    if uid and m_type:
        data = uo.get_user_info(uid)
        if data:
            return pl.get_cache_list(data["uid"], m_type)
        else:
            return config.build_response('get_list', '', 501)
    else:
        return config.build_response('get_list', '', 502)


@logic.route('/get_file_info', methods=['POST'])
def get_audio_info():
    uid = request.form['uid']
    fid = request.form['fid']
    if uid and fid:
        data = uo.get_user_info(uid)
        if data:
            return config.build_response('get_file_info', pl.get_file_info([fid]), 200)
        else:
            return config.build_response('get_file_info', '', 501)
    else:
        return config.build_response('get_file_info', '', 502)


@logic.route('/get_music_info', methods=['POST'])
def get_info():
    uid = request.form['uid']
    song_name = request.form['song_name']
    if uid and song_name:
        data = uo.get_user_info(uid)
        if data:
            return config.build_response('get_music_info', pl.ls.search_song_by_name(song_name), 200)
        else:
            return config.build_response('get_music_info', '', 501)
    else:
        return config.build_response('get_music_info', '', 502)


@logic.route('/update_music_info', methods=['POST'])
def update_info():
    uid = request.form['uid']
    fid = request.form['fid']
    song_id = request.form['song_id']
    artist = request.form['artist']
    album = request.form['album']
    if uid and song_id and fid:
        data = uo.get_user_info(uid)
        if data:
            if artist != '' and album != '':
                return config.build_response('update_music_info', pl.ls.update_music_info(fid, song_id, artist, album),
                                             200)
            elif artist != '':
                return config.build_response('update_music_info', pl.ls.update_music_info(fid, song_id, artist=artist),
                                             200)
            elif album != '':
                return config.build_response('update_music_info', pl.ls.update_music_info(fid, song_id, album=album),
                                             200)
            else:
                return config.build_response('update_music_info', pl.ls.update_music_info(fid, song_id), 200)
        else:
            return config.build_response('update_music_info', '', 501)
    else:
        return config.build_response('update_music_info', '', 502)
