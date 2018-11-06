import json
import re

from bson import ObjectId

from server_utils.HttpRequestBase import HttpRequestBase


class LyricSpider:
    def __init__(self, mongo):
        self.Http = HttpRequestBase(timeout=200, retries=20)
        self.__mongo = mongo
        self.__file_info = 'file_store.files'
        self.search_song_url = 'http://music.163.com/api/search/get/web?s={0}&type={1}&offset=0&total=true&limit={2}'
        self.search_lyric_url = 'http://music.163.com/api/song/lyric?os=pc&id={0}&lv=-1&kv=-1&tv=-1'

    def search_song_by_name(self, song_name, limit=3):
        song_list = []
        try:
            resp = self.Http.requests_request('POST', self.search_song_url.format(song_name, 1, limit))
            if resp != '':
                _info = json.loads(resp)
                if _info['code'] == 200 and _info['result'].__contains__('songs'):
                    if _info['result']['songCount'] > 0:
                        for each in _info['result']['songs']:
                            song_list.append({
                                'song_id': each['id'],
                                'song_name': each['name'],
                                'artist': each['artists'][0]['name'] if len(each['artists']) > 0 else 'UNKNOWN',
                                'album': each['album']['name'] if each['album'].__contains__('name') > 0 else 'UNKNOWN',
                                'lyric': self.get_song_lyric(each['id'])
                            })
        except:
            pass
        return song_list

    def get_song_lyric(self, song_id):
        resp = self.Http.requests_request('POST', self.search_lyric_url.format(song_id))
        lyric = None
        if resp != '':
            _info = json.loads(resp)
            if _info['code'] == 200 and not _info.__contains__('uncollected') and not _info.__contains__('nolyric'):
                lyr_str = _info['lrc']['lyric']
                lyric = self._parse_lyric(lyr_str)
            else:
                lyric = 'UNKNOWN'
        return lyric

    def update_music_info(self, fid, song_id, artist=None, album=None):
        try:
            _info = self.search_song_by_name(song_id, 1)
            if len(_info) > 0:
                if self.__mongo.exist(self.__file_info, {'_id': ObjectId(fid)}):
                    file_info = self.__mongo.search_by_kv_pair(self.__file_info, {'_id': ObjectId(fid)})[0]
                    des = json.loads(file_info['description'])
                    des['artist'] = artist if artist else _info[0]['artist']
                    des['album'] = album if album else _info[0]['album']
                    des['lyric'] = _info[0]['lyric']
                    self.__mongo.update(self.__file_info, {'_id': ObjectId(fid)},
                                        {'$set': {'description': json.dumps(des)}})
        except json.JSONDecodeError:
            return False
        return True

    def _parse_lyric(self, lrc):
        lyric = []
        parse_line = r"\[\d{2}:\d{2}.\d{2}\][\s]?[\u4e00-\u9fa5-A-Za-z0-9\s:]*"
        parse_time = r"\d{2}:\d{2}.\d{2}"
        line_parser = re.compile(parse_line)
        time_parser = re.compile(parse_time)
        lrc_lines = line_parser.findall(lrc)
        for each in lrc_lines:
            l_time = time_parser.findall(each)[0]
            lp_time = self.my_split(str(l_time).split(), [':', '.'])
            seconds = float(lp_time[0]) * 60 + float(lp_time[1]) + float('0.' + lp_time[2])
            l_text = each.replace(f'[{l_time}]', '').replace('\n', '')
            lyric.append({
                'sec': seconds,
                'text': l_text
            })
        return lyric

    @staticmethod
    def my_split(s, sign):
        for i in sign:
            t = []
            for x in s:
                def lambed(i, t, x, s):
                    map(t.extend(x.split(i)), s)

                lambed(i, t, x, s)
            s = t
        return s
