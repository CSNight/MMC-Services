import time

from bson import ObjectId

from config import GetConfig
from server_utils.MongoDBOP import MongoDBOP


class MovieCache:
    def __init__(self):
        self.__mongo = MongoDBOP(**config.get_mongo_connection())
        self.__file_store = "file_store.chunks"

    def get_part(self, fid):
        st = time.process_time()
        res = self.__mongo.search_by_kv_pair(self.__file_store, {"files_id": ObjectId(fid)})
        cache_bytes = bytes.join(bytes(), map(lambda each: each['data'], res))
        with open("f:\\ea.mp4", "ab") as f:
            f.write(cache_bytes)
            f.flush()
        end = time.process_time()
        print(end - st)


config = GetConfig()
m = MovieCache()
m.get_part("5b10070bfb4bf90ad04d2075")
