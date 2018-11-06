import mimetypes
import os
import tarfile
import uuid
import zipfile
from io import BytesIO

import pythoncom
import rarfile
from PIL import Image
from flask import Blueprint, request, make_response, render_template
from win32com.client import Dispatch

from config import GetConfig
from server_utils.MongoDBOP import MongoDBOP
from user_manage.user_views import uo


class FileTransform:
    def __init__(self):
        self.__mongo = MongoDBOP(**config.get_mongo_connection())
        self.__file_set = "file_store"
        self.__short_cut = "video_shortcut"
        self.__collection = "user_data_tree"

    def get_shortcut(self, fid, f_type):
        img_f = None
        if f_type == 'image':
            if self.__mongo.check_file(self.__file_set, fid):
                factor = 158 / 180
                img_f = self.__mongo.get_file(self.__file_set, fid)
                img = Image.open(img_f)
                img = img.convert('RGB')
                if (img.size[0] / img.size[1]) < factor:
                    img = img.resize((158, 180), Image.ANTIALIAS)
                buf = BytesIO()
                img.save(buf, 'jpeg')
                response = make_response(buf.getvalue())
                del img, buf
            else:
                response = make_response('not_found')
        elif f_type == 'audio':
            if self.__mongo.check_file(self.__short_cut, fid):
                img_f = self.__mongo.get_file(self.__short_cut, fid)
                img = Image.open(img_f)
                img = img.convert('RGB')
                img = img.resize((128, 128), Image.ANTIALIAS)
                buf = BytesIO()
                img.save(buf, 'jpeg')
                response = make_response(buf.getvalue())
                del img, buf
            else:
                response = make_response('not_found')
        else:
            img_f = self.__mongo.get_file(self.__short_cut, fid)
            response = make_response(img_f.read())
        response.headers['Content-Type'] = 'image/jpeg'
        del img_f
        return response

    def get_package_list(self, fid, ext):
        chd = str(uuid.uuid4())
        tmp_path = config.get_tmp_by_type("package") + '\\' + chd + '\\'
        os.makedirs(tmp_path)
        pkg_input = tmp_path + str(uuid.uuid4()) + ext
        if self.__mongo.check_file(self.__file_set, fid):
            db_file = self.__mongo.get_file(self.__file_set, fid)
            file_name = db_file._file['file_name']
            with open(pkg_input, 'wb') as f:
                f.write(db_file.read())
                f.flush()
            del db_file
            try:
                if ext == '.zip':
                    zip_file = zipfile.ZipFile(pkg_input)
                    fl = zip_file.namelist()
                    zip_file.close()
                elif ext == '.rar':
                    rar_file = rarfile.RarFile(pkg_input)
                    fl = rar_file.namelist()
                    rar_file.close()
                elif ext == '.gz':
                    tar_file = tarfile.open(pkg_input)
                    fl = tar_file.getnames()
                    tar_file.close()
                else:
                    fl = []
            except Exception:
                fl = []
            finally:
                if os.path.isfile(pkg_input) and os.path.exists(tmp_path):
                    os.remove(pkg_input)
                    os.rmdir(tmp_path)
            fl.sort(key=lambda x: len(x))
            return render_template('pkg_list.html', filename=file_name, tree=self.__gen_list(fl, ext))
        else:
            return config.build_response('zip_list', "", 103)

    @classmethod
    def __gen_list(cls, pkg_list, ext):
        dir_tree = {
            'fp': '...',
            'xp': '...',
            'children': []
        }
        dir_deep = 0
        for each in pkg_list:
            tmp_deep = str(each).count('/')
            if tmp_deep > dir_deep:
                dir_deep = tmp_deep
        for each in pkg_list:
            if ext == '.zip':
                mp = each.rstrip('/')
                if str(mp).count('/') == 0:
                    f = {'fp': each, 'xp': each, 'children': []}
                    dir_tree['children'].append(f)
            else:
                if str(each).count('/') == 0:
                    f = {'fp': each, 'xp': each, 'children': []}
                    dir_tree['children'].append(f)

        def recursion(deep, lists):
            for i in lists:
                for itm in pkg_list:
                    if ext == '.zip':
                        tt = itm.rstrip('/')
                        if str(tt).count('/') == deep and itm.__contains__(i['fp']):
                            tmp = {'fp': itm, 'xp': str(itm).replace(i['fp'], '').lstrip('/'), 'children': []}
                            i['children'].append(tmp)
                    else:
                        if str(itm).count('/') == deep and itm.__contains__(i['fp']):
                            tmp = {'fp': itm, 'xp': str(itm).replace(i['fp'], '').lstrip('/'), 'children': []}
                            i['children'].append(tmp)
                for rm in i['children']:
                    pkg_list.remove(rm['fp'])
                recursion(deep + 1, i['children'])

        recursion(1, dir_tree['children'])
        return dir_tree

    def office_to_pdf(self, fid, ext):
        chd = str(uuid.uuid4())
        tmp_path = config.get_tmp_by_type("doc") + '\\' + chd + '\\'
        os.makedirs(tmp_path)
        office_input = tmp_path + str(uuid.uuid4()) + ext
        fn = str(uuid.uuid4()) + '.pdf'
        office_output = tmp_path + fn
        if self.__mongo.check_file(self.__file_set, fid):
            db_file = self.__mongo.get_file(self.__file_set, fid)
            with open(office_input, 'wb') as f:
                f.write(db_file.read())
                f.flush()
            del db_file
            try:
                pythoncom.CoInitialize()
                if ext == '.doc' or ext == '.docx':
                    FileTransform.__word_to_pdf(office_input, office_output)
                elif ext == '.xls' or ext == '.xlsx':
                    FileTransform.__excel_to_pdf(office_input, office_output)
                elif ext == '.ppt' or ext == '.pptx':
                    FileTransform.__ppt_to_pdf(office_input, office_output)
                elif ext == '.txt':
                    fn = os.path.split(office_input)[1]
                    office_output = office_input
                elif ext == '.vsd' or ext == '.vsdx':
                    FileTransform.__visio_to_pdf(office_input, office_output)
                if os.path.isfile(office_output):
                    return config.build_response('office_trans', {'name': fn, "chd": chd}, 200)
                else:
                    return config.build_response('office_trans', "", 103)
            except Exception:
                return config.build_response('office_trans', "", 103)
        else:
            return config.build_response('office_trans', '', 300)

    @staticmethod
    def __word_to_pdf(input_f, output_f):
        """Word.ExportAsFixedFormat():
            :param: Output_file
            :param: Format  pdf=17 xps=18
            :param: openAfterExport  default True
            :param: ExportOptimizeFor  default For Printer=0 For Screen=1
            :param: openAfterExport  default True
            :param: ExportRange  default All=0,FromTo=3,currentPage=2,Selection=1
            :param: From  default 1
            :param: To  default 1
            :param: ExportItem  default Content=0,ContentWithMarkUp=7
            :param: ContainDocProp  default True
            :param: KeepIRM  default True
            :param: CreateBookMark default 1
            :param: DocStructureMark default True
            :param: BitmapMissingFont default True
            :param: UseISO default True
        """
        word = Dispatch("Word.Application")
        try:
            doc = word.Documents.Open(input_f, ReadOnly=1)
            doc.ExportAsFixedFormat(output_f, 17, False, 0, 0, 1, 1, 0, True, True, 1, True, True, False)
            doc.Close()
        except IOError or ValueError or AttributeError or KeyError or TypeError:
            pass
        finally:
            word.Quit(SaveChanges=0)
            if os.path.exists(input_f):
                os.remove(input_f)

    @staticmethod
    def __excel_to_pdf(input_f, output_f):
        """Excel.ExportAsFixedFormat():
            :param: Format  pdf=0 xps=1
            :param: Output_file
            :param: Quality QualityStandard=0 mini=1
            :param: ContainDocProp  default True
            :param: IgnorePrintArea
            :param: From  default 1
            :param: To  default 1
            :param: openAfterExport  default True
            :param: FixedFormatExtClassPtr don't need' \
        """
        excel = Dispatch("Excel.Application")
        try:
            exl = excel.Workbooks.Open(input_f, ReadOnly=1)
            exl.ExportAsFixedFormat(0, output_f, Quality=0, IncludeDocProperties=True, OpenAfterPublish=False)
            exl.Close()
        except IOError or ValueError or AttributeError or KeyError or TypeError:
            pass
        finally:
            excel.Quit()
            if os.path.exists(input_f):
                os.remove(input_f)

    @staticmethod
    def __ppt_to_pdf(input_f, output_f):
        """PowerPoint.ExportAsFixedFormat():
            :param: Output_file
            :param: Format pdf=2,xps=1
            :param: FixedFormatIntent default For Printer=2 For Screen=1,
            :param: FrameSlides = 0,
            :param: PrintHandoutOrder VerticalFirst=1,HorizontalFirst=2
            :param: PrintOutputType.PrintOutputSlides=1,
            :param: PrintHiddenSlides = 0,
            :param: PrintRange = null,
            :param: RangeType PrintAll=1,
            :param: SlideShowName = "",
            :param: IncludeDocProperties default false
            :param: KeepIRMSettings  default true
            :param: DocStructureTags  default true
            :param: BitmapMissingFonts default true
            :param: UseISO19005_1  default false don't need
            :param: ExternalExporter default null don't need
        """
        ppt = Dispatch("PowerPoint.Application")
        ppt.Visible = 1
        try:
            ppt_doc = ppt.Presentations.Open(input_f, ReadOnly=1)
            ppt_doc.ExportAsFixedFormat(output_f, 2, 2, 0, 1, 1, 0, None, 1, "", 1, True, True, True, True)
            ppt_doc.Close()
        except IOError or ValueError or AttributeError or KeyError or TypeError:
            pass
        finally:
            ppt.Quit()
            if os.path.exists(input_f):
                os.remove(input_f)

    @staticmethod
    def __visio_to_pdf(input_f, output_f):
        """Visio.ExportAsFixedFormat():
            :param: Format pdf=1,xps=2
            :param: Output_file
            :param: FixedFormatIntent default For Printer=1 For Screen=0,
            :param: ExportRange  default All=0,currentView=4,currentPage=2,Selection=3,FromTo=1
            :param: From  default 1
            :param: To  default -1
            :param: ColorAsBlack default false
            :param: IncludeBackground  default true
            :param: IncludeDocumentProperties  default true
            :param: IncludeStructureTags default true
            :param: UseISO19005_1  default false don't need
        """
        vis = Dispatch("Visio.Application")
        try:
            vis_doc = vis.Documents.Open(input_f)
            vis_doc.ExportAsFixedFormat(1, output_f, 1, 0, 1, -1, False, True, True, True, False)
            vis_doc.Close()
        except IOError or ValueError or AttributeError or KeyError or TypeError:
            pass
        finally:
            vis.Quit()
            if os.path.exists(input_f):
                os.remove(input_f)


config = GetConfig()
ft = FileTransform()
trans = Blueprint('trans', __name__)


@trans.route('/office_pdf', methods=['GET'])
def doc_convert():
    uid = request.args.get('uid')
    fid = request.args.get('fid')
    ext = request.args.get('ext')
    if uid and fid and ext:
        data = uo.get_user_info(uid)
        if data:
            return ft.office_to_pdf(fid, ext)
        else:
            return config.build_response('office_pdf', '', 501)
    else:
        return config.build_response('office_pdf', '', 502)


@trans.route('/get_preview', methods=['GET'])
def get_preview():
    uid = request.args.get('uid')
    fid = request.args.get('fid')
    f_type = request.args.get('f_type')
    if uid and fid and f_type:
        data = uo.get_user_info(uid)
        if data:
            return ft.get_shortcut(fid, f_type)
        else:
            return config.build_response('get_preview', '', 501)
    else:
        return config.build_response('get_preview', '', 502)


@trans.route('/resource/<f_type>/<path>/<name>', methods=['GET'])
def get_file(f_type, path, name):
    tmp_path = config.get_tmp_by_type(f_type) + '\\' + path + "\\" + name
    mime_type = mimetypes.guess_type(name)[0]
    if os.path.isfile(tmp_path):
        with open(tmp_path, 'rb+')as f:
            response = make_response(f.read())
            f.close()
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Type'] = mime_type
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    else:
        return config.build_response('resource', '', 101)


@trans.route('/zip_list', methods=['GET'])
def zip_list():
    uid = request.args.get('uid')
    fid = request.args.get('fid')
    ext = request.args.get('ext')
    if uid and fid and ext:
        data = uo.get_user_info(uid)
        if data:
            return ft.get_package_list(fid, ext)
        else:
            return config.build_response('zip_list', '', 501)
    else:
        return config.build_response('zip_list', '', 502)
