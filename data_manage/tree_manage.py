import json
import os
import time
import uuid

from flask import request, Blueprint

from config import GetConfig
from server_utils.MongoDBOP import MongoDBOP
from user_manage.user_views import uo


class DataTree:
    def __init__(self):
        self.__mongo = MongoDBOP(**config.get_mongo_connection())
        self.__collection = "user_data_tree"
        self.__file_set = "file_store"
        self.__icon_set = "icon"
        self.__short_cut = "video_shortcut"
        self.node_tem = {
            "id": "",
            "pid": "",
            "uid": "",
            "name": "",
            "icon": "",
            "children": [],
            "data": []
        }
        self.data_tem = {
            "fid": "",
            "f_type": "",
            "file_name": "",
            "file_type": "",
            "file_size": 0.0,
            "create_time": 0.0,
            "description": ""
        }

    def new_node(self, uid, name, pid=None, icon=None, children=None, data=None):
        node = self.node_tem.copy()
        node["id"] = str(uuid.uuid4())
        node["name"] = name if name and isinstance(name, str) else ""
        node["pid"] = pid if pid and isinstance(pid, str) else ""
        node["uid"] = uid if uid and isinstance(uid, str) else ""
        node["icon"] = icon if icon and isinstance(icon, str) else ""
        node["children"] = children if children and isinstance(data, list) else []
        node["data"] = data if data and isinstance(data, list) else []
        return node

    def new_file(self, file_name, f_path, f_type, description=None):
        n_file = self.data_tem.copy()
        n_file["fid"] = ""
        n_file["f_type"] = f_type
        n_file["file_name"] = file_name
        n_file["file_type"] = os.path.splitext(f_path)[1]
        n_file["file_size"] = round(os.path.getsize(f_path) / float(1024 * 1024), 2)
        n_file["create_time"] = time.time()
        n_file["description"] = description if description and isinstance(description, str) else ""
        return n_file

    @staticmethod
    def __remove_oid(target):
        if dict(target).__contains__("_id"):
            del target["_id"]
        return target

    def create_tree(self, uid):
        user_tree = self.new_node(uid, "root", icon="mif-tree")
        if self.__mongo.exist(self.__collection, {"uid": uid, "name": "root"}):
            self.__mongo.delete(self.__collection, {"uid": uid, "name": "root"})
        res = self.__mongo.insert(self.__collection, user_tree.copy())
        if res is not None:
            return config.build_response("create_tree", user_tree, 200)
        else:
            return config.build_response("create_tree", "", 300)

    def del_tree(self, uid):
        res = self.__mongo.search_by_kv_pair(self.__collection, {"uid": uid})
        op_list = []
        data_list = []
        for each in res:
            op_list.append({"id": each["id"]})
            data_list.extend(each["data"])
        res = self.__mongo.bulk_operation(self.__collection, op_list, "delete")
        self.__mongo.delete_files(self.__file_set, data_list)
        op_count = len(op_list)
        del op_list
        if res.deleted_count == op_count:
            return config.build_response("del_tree", {"nodes": res.deleted_count, "file": len(data_list)}, 200)
        else:
            return config.build_response("del_tree", "", 300)

    def get_tree(self, uid):
        res = self.__mongo.search_by_kv_pair(self.__collection, {"uid": uid, "name": "root"})
        res_child = self.__mongo.search_by_kv_pair(self.__collection, {"uid": uid, "name": {"$ne": "root"}})
        if len(res) > 0:
            root = self.__remove_oid(res[0])
            self.get_node(root, res_child)
            return config.build_response("get_tree", root, 200)
        else:
            return config.build_response("get_tree", "", 102)

    def get_node(self, root, res_child):
        children = root["children"]
        root["childes"] = []
        for each in children:
            for x in res_child:
                if x["id"] == each:
                    x["childes"] = []
                    if len(x["children"]) > 0:
                        self.get_node(x, res_child)
                    root["childes"].append(self.__remove_oid(x))

    def add_node(self, uid, pid, name, icon=None):
        node = self.new_node(uid, name, pid, icon)
        res_in = self.__mongo.insert(self.__collection, node.copy())
        res_up = self.__mongo.update(self.__collection, {"id": pid}, "$push", {"children": node["id"]})
        if res_up and res_in:
            return config.build_response("add_node", node, 200)
        else:
            return config.build_response("add_node", "", 300)

    def rename_node(self, sid, name, icon="mif-folder"):
        res = self.__mongo.search_by_kv_pair(self.__collection, {"id": sid})
        if len(res) > 0:
            if res[0]["name"] != "root":
                res_up = self.__mongo.update(self.__collection, {"id": sid}, "$set", {"name": name, "icon": icon})
                if res_up:
                    return config.build_response("rename_node", "", 200)
                else:
                    return config.build_response("rename_node", "", 300)
            else:
                return config.build_response("rename_node", 'can"t rename root', 300)
        else:
            return config.build_response("rename_node", 'node doesn"t find', 300)

    def del_node(self, uid, sid):
        try:
            res_self = self.__mongo.search_by_kv_pair(self.__collection, {"uid": uid, "id": sid})
            if res_self[0].get("pid"):
                if self.__mongo.exist(self.__collection, {"id": res_self[0]["pid"]}):
                    self.__mongo.update(self.__collection, {"id": res_self[0]["pid"]}, "$pull", {"children": sid})
            index = [0, 0]
            self.reload_del(uid, sid, index)
            return config.build_response("del_node", {"delete_count": index}, 200)
        except:
            return config.build_response("del_node", "", 300)

    def reload_del(self, uid, sid, index):
        res_self = self.__mongo.search_by_kv_pair(self.__collection, {"uid": uid, "id": sid})
        op_list = []
        data_list = []
        children = []
        for each in res_self:
            op_list.append({"id": each["id"]})
            data_list.extend(list(map(lambda item: item["fid"], each["data"])))
            children = each["children"]
            index[0] = index[0] + 1
            index[1] = index[1] + len(data_list)
        self.__mongo.bulk_operation(self.__collection, op_list, "delete")
        self.__mongo.delete_files(self.__file_set, data_list)
        for each in children:
            self.reload_del(uid, each, index)

    def add_file(self, uni_id, f_type, description, sid):
        tmp_path = config.get_tmp_by_type(f_type) + "\\" + uni_id + "\\"
        file_list = [(tmp_path + i) for i in os.listdir(tmp_path)]
        descriptions = json.loads(description)
        rsp = []
        for i, f_path in enumerate(file_list):
            if os.path.isfile(f_path):
                n_file = self.new_file(os.path.split(f_path)[1], f_path, f_type, str(descriptions[f_path]))
                fid = self.__mongo.insert_singlefile_by_path(self.__file_set, f_path, n_file)
                if fid and self.__mongo.exist(self.__collection, {"id": sid}):
                    os.remove(f_path)
                    n_file["fid"] = fid
                    res = self.__mongo.update(self.__collection, {"id": sid}, "$push", {"data": n_file})
                    if res.modified_count == 1:
                        rsp.append(n_file)
                    else:
                        rsp.append({"fid": fid, "status": False})
                else:
                    rsp.append({"fid": "", "status": False})
            else:
                rsp.append({"fid": "", "status": False})
        os.rmdir(tmp_path)
        return config.build_response("add_file", rsp, 200)

    def del_file(self, sid, fid):
        try:
            file_node = self.__mongo.search_by_kv_pair(self.__collection, {"id": sid})
            if len(file_node) > 0:
                tmp = []
                data_files = file_node[0]["data"]
                for each in data_files:
                    if each["fid"] == fid:
                        if each["description"] != "{}":
                            dict_info = json.loads(each["description"].replace('\\', "").replace('\'', "\""))
                            if dict_info['shortcut'] != "UNKNOWN" and dict_info['shortcut'] != "":
                                self.__mongo.delete_files(self.__short_cut, [dict_info['shortcut']])
                        continue
                    tmp.append(self.__remove_oid(each))
                if self.__mongo.check_file(self.__file_set, fid):
                    self.__mongo.delete_files(self.__file_set, [fid])
                self.__mongo.update(self.__collection, {"id": sid}, "$set", {"data": tmp})
                return config.build_response("del_file", fid, 200)
            else:
                return config.build_response("del_file", fid, 101)
        except:
            return config.build_response("del_file", "", 300)

    def count_user_file(self, uid, f_type, rsp_t):
        data_nodes = []
        res = self.__mongo.search_by_kv_pair(self.__collection, {"uid": uid})
        for each in res:
            data_nodes.extend(each["data"])
        if rsp_t == "count_all":
            type_dic = {"doc": 0, "video": 0, "audio": 0, 'image': 0, "package": 0}
            for key in type_dic:
                for data in data_nodes:
                    if data["f_type"] == key:
                        type_dic[key] += 1
            return config.build_response("count_file", type_dic, 200)
        elif rsp_t == "count_single":
            count = 0
            for data in data_nodes:
                if data["f_type"] == f_type:
                    count += 1
            return config.build_response("count_file", count, 200)
        else:
            col = []
            for data in data_nodes:
                if data["f_type"] == f_type:
                    col.append(data)
            return config.build_response("count_file", col, 200)

    def get_icons(self):
        res = self.__mongo.search_by_kv_pair(self.__icon_set, {})
        icons = {}
        for each in res:
            each = self.__remove_oid(each)
            for key in each.keys():
                icons[key] = each[key]
        return config.build_response("get_icons", icons, 200)


config = GetConfig()
dt = DataTree()
tree = Blueprint("tree", __name__)


@tree.route("/get_tree", methods=["POST"])
def get_user_tree():
    uid = request.form["uid"]
    if uid:
        data = uo.get_user_info(uid)
        if data:
            return dt.get_tree(data["uid"])
        else:
            return config.build_response("get_tree", "", 501)
    else:
        return config.build_response("get_tree", "", 502)


@tree.route("/create_tree", methods=["GET"])
def create_user_tree():
    uid = request.args.get("uid")
    if uid:
        data = uo.get_user_info(uid)
        if data:
            return dt.create_tree(data["uid"])
        else:
            return config.build_response("create_tree", "", 501)
    else:
        return config.build_response("create_tree", "", 502)


@tree.route("/del_tree", methods=["GET"])
def del_user_tree():
    uid = request.args.get("uid")
    if uid:
        data = uo.get_user_info(uid)
        if data:
            return dt.del_tree(data["uid"])
        else:
            return config.build_response("del_tree", "", 501)
    else:
        return config.build_response("del_tree", "", 502)


@tree.route("/add_node", methods=["GET"])
def add_tree_node():
    uid = request.args.get("uid")
    pid = request.args.get("pid")
    name = request.args.get("name")
    icon = request.args.get("icon")
    if uid and pid and name:
        data = uo.get_user_info(uid)
        if data:
            return dt.add_node(data["uid"], pid, name, icon)
        else:
            return config.build_response("add_node", "", 501)
    else:
        return config.build_response("add_node", "", 502)


@tree.route("/rename_node", methods=["GET"])
def rename_tree_node():
    uid = request.args.get("uid")
    sid = request.args.get("sid")
    name = request.args.get("name")
    icon = request.args.get("icon")
    if uid and sid and name:
        data = uo.get_user_info(uid)
        if data:
            if icon:
                return dt.rename_node(sid, name, icon)
            else:
                return dt.rename_node(sid, name)
        else:
            return config.build_response("rename_node", "", 501)
    else:
        return config.build_response("rename_node", "", 502)


@tree.route("/del_node", methods=["GET"])
def del_tree_node():
    uid = request.args.get("uid")
    sid = request.args.get("sid")
    if uid and sid:
        data = uo.get_user_info(uid)
        if data:
            return dt.del_node(data["uid"], sid)
        else:
            return config.build_response("del_node", "", 501)
    else:
        return config.build_response("del_node", "", 502)


@tree.route("/del_file", methods=["GET"])
def del_node_file():
    uid = request.args.get("uid")
    sid = request.args.get("sid")
    fid = request.args.get("fid")
    if uid and fid and sid:
        data = uo.get_user_info(uid)
        if data:
            return dt.del_file(sid, fid)
        else:
            return config.build_response("del_file", "", 501)
    else:
        return config.build_response("del_file", "", 502)


@tree.route("/add_file", methods=["POST"])
def add_node_file():
    uid = request.form["uid"]
    uni_id = request.form["unique_id"]
    sid = request.form["sid"]
    f_type = request.form["f_type"]
    description = request.form["description"]
    if uid and uni_id and sid and f_type:
        data = uo.get_user_info(uid)
        if data:
            return dt.add_file(uni_id, f_type, description, sid)
        else:
            return config.build_response("add_file", "", 501)
    else:
        return config.build_response("add_file", "", 502)


@tree.route("/count_file", methods=["GET"])
def count_files():
    uid = request.args.get("uid")
    f_type = request.args.get("f_type")
    rsp_t = request.args.get("response_t")
    if uid and f_type and rsp_t:
        data = uo.get_user_info(uid)
        if data:
            return dt.count_user_file(data["uid"], f_type, rsp_t)
        else:
            return config.build_response("count_file", "", 501)
    else:
        return config.build_response("count_file", "", 502)


@tree.route("/get_icons", methods=["POST", "GET"])
def get_icons_set():
    return dt.get_icons()
