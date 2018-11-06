import os
import threading
import time

from bson.objectid import ObjectId
from gridfs import GridFS
from pymongo import ASCENDING, DESCENDING
from pymongo.mongo_client import MongoClient
from pymongo.operations import InsertOne, UpdateOne, DeleteOne


class MongoDBOP:
    def __init__(self, host, port, db=None, user=None, pwd=None):
        self.host = host
        self.port = port
        self.instance = MongoClient(host, port, retryWrites=True)
        self.db = self.instance.get_database(
            name=db) if db in self.instance.list_database_names() else self.instance.admin
        self.user = user
        self.pwd = pwd
        self.globalLock = threading.Lock()
        if self.user and self.pwd:
            self.db.authenticate(name=user, password=pwd)

    def release_db(self, set_name):
        self.globalLock.acquire()
        res = self.db.command({"compact": set_name})
        self.globalLock.release()
        if res.__contains__('ok'):
            if res['ok'] == 1.0:
                return True
            else:
                return False
        else:
            return False

    def close(self):
        self.instance.close()

    def insert(self, set_name, data):
        return self.db[set_name].insert(data)

    def drop_col(self, set_name):
        return self.db[set_name].drop()

    def delete(self, set_name, data):
        return self.db[set_name].delete_one(data)

    def update(self, set_name, search, _op, data):
        return self.db[set_name].update_one(search, {_op: data})

    def multi_update(self, set_name, search, _op, data):
        return self.db[set_name].update(search, {_op: data}, multi=True)

    def exist(self, set_name, search):
        res = self.db[set_name].find_one(search)
        if res:
            return True
        else:
            return False

    def bulk_operation(self, set_name, data_list, operation_type, ordered=False):
        requests = []
        if operation_type == "insert":
            requests = list(map(lambda doc: InsertOne(doc), data_list))
        elif operation_type == "update":
            requests = list(map(lambda info: UpdateOne(filter=info[0], update=info[1]), data_list))
        elif operation_type == "delete":
            requests = list(map(lambda info: DeleteOne(filter=info), data_list))
        elif operation_type == "multi_type":
            for key in data_list.keys():
                if data_list[key]["op_type"] == "insert":
                    requests.append(InsertOne(data_list[key]["info"]))
                elif data_list[key]["op_type"] == "update":
                    requests.append(UpdateOne(filter=data_list[key]["info"][0], update=data_list[key]["info"][1]))
                elif data_list[key]["op_type"] == "delete":
                    requests.append(DeleteOne(data_list[key]["info"]))
        return self.db[set_name].bulk_write(requests, ordered=ordered)

    def insert_file_stream(self, set_name, file_name, ext, stream, info_dic=None):
        self.globalLock.acquire()
        try:
            grid_fs = GridFS(self.db, collection=set_name)
            if info_dic is None:
                info_dic = {"content_type": ext, "file_name": file_name, "timestamp": time.time()}
            else:
                info_dic["content_type"] = ext
                info_dic["file_name"] = file_name
                info_dic["timestamp"] = time.time()
            _object_id = str(grid_fs.put(stream, **info_dic))
            return _object_id
        except:
            return None
        finally:
            self.globalLock.release()

    def insert_singlefile_by_path(self, set_name, file_path, info_dic=None):
        self.globalLock.acquire()
        try:
            grid_fs = GridFS(self.db, collection=set_name)
            path, file_name = os.path.split(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            if os.path.isfile(file_path):
                with open(file_path, 'rb+') as f:
                    data = f.read()
                    if info_dic is None:
                        info_dic = {"content_type": file_ext, "file_name": file_name, "timestamp": time.time()}
                    else:
                        info_dic["content_type"] = file_ext
                        info_dic["file_name"] = file_name
                        info_dic["timestamp"] = time.time()
                    _object_id = str(grid_fs.put(data, **info_dic))
                return _object_id
            else:
                return None
        finally:
            self.globalLock.release()

    def insert_files(self, set_name, file_paths, info_dicts=None):
        self.globalLock.acquire()
        try:
            grid_fs = GridFS(self.db, collection=set_name)
            id_cols = []
            if not isinstance(file_paths, (list, tuple)) and os.path.exists(file_paths):
                file_paths = [file_paths + "\\" + x for x in os.listdir(file_paths)]
            if info_dicts is None:
                info_dicts = [None] * len(file_paths)
            for i, each in enumerate(file_paths):
                path, file_name = os.path.split(each)
                file_ext = os.path.splitext(each)[1].lower()
                if os.path.isfile(each):
                    with open(each, 'rb') as f:
                        data = f.read()
                        if info_dicts[i] is None:
                            info_dicts[i] = {"content_type": file_ext, "file_name": file_name, "timestamp": time.time()}
                        else:
                            info_dicts[i]["content_type"] = file_ext
                            info_dicts[i]["file_name"] = file_name
                            info_dicts[i]["timestamp"] = time.time()
                        _object_id = str(grid_fs.put(data, **info_dicts[i]))
                        f.close()
                        id_cols.append(_object_id)
            return id_cols
        finally:
            self.globalLock.release()

    def get_file(self, set_name, fid):
        self.globalLock.acquire()
        try:
            grid_fs = GridFS(self.db, collection=set_name)
            file = grid_fs.get(ObjectId(fid))
            return file
        finally:
            self.globalLock.release()

    def check_file(self, set_name, fid):
        grid_fs = GridFS(self.db, collection=set_name)
        status = grid_fs.exists(ObjectId(fid))
        return status

    def delete_files(self, set_name, ids):
        self.globalLock.acquire()
        try:
            grid_fs = GridFS(self.db, collection=set_name)
            for each in ids:
                if grid_fs.exists(document_or_id=ObjectId(each)):
                    grid_fs.delete(ObjectId(each))
        finally:
            self.globalLock.release()

    def search_by_kv_pair(self, set_name, filters, logic_type=None, sort_list=None, limit=None, skip=None):
        cursor = None
        if logic_type is None and isinstance(filters, dict):
            cursor = self.db[set_name].find(filters)
        elif logic_type == "or" and isinstance(filters, list):
            cursor = self.db[set_name].find({"$or": filters})
        if sort_list is not None:
            for key in sort_list:
                if key[1] == "ASC":
                    key[1] = ASCENDING
                else:
                    key[1] = DESCENDING
            cursor = cursor.sort(sort_list)
        if skip is not None:
            cursor = cursor.skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)
        res_list = []
        for each in cursor:
            res_list.append(each)
        return res_list

    def find_count(self, set_name, filters, logic_type=None):
        count = 0
        if logic_type is None and isinstance(filters, dict):
            count = self.db[set_name].find(filters).count()
        elif logic_type == "or" and isinstance(filters, list):
            count = self.db[set_name].find({"$or": filters}).count()
        return count
