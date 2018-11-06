import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import chardet
import requests
import urllib3


class HttpRequestBase:
    def __init__(self, params=None, headers=None, timeout=200, retries=20, redirect=False, proxys=None):
        self.__agent = [
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
            'Opera/9.25 (Windows NT 5.1; U; en)',
            'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
            'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
            'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12',
            'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9',
            "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0 ",
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:5.0)',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
        ]
        if headers is not None:
            self.__headers = headers
        else:
            self.__headers = {
                'User-Agent': random.choice(self.__agent)
            }
        self.timeout = timeout
        self.retries = retries
        self.redirect = redirect
        self.param = params
        self.proxys = proxys

    def requests_request(self, method, url, codec=False, data=None):
        try:
            res = requests.request(method, url=url, params=self.param, data=data, headers=self.__headers,
                                   timeout=self.timeout, allow_redirects=self.redirect, proxies=self.proxys)
            if res.status_code == 200:
                content = res.content
                code = chardet.detect(content)["encoding"]
                del content
                if code is not None:
                    if codec:
                        res.encoding = 'gbk'
                    else:
                        res.encoding = code
                    text = res.text
                    res.close()
                    del res
                    return text
                else:
                    res.encoding = "utf-8"
                    text = res.text
                    res.close()
                    del res
                    return text
            elif res.status_code == 404 or res.status_code == 500 or res.status_code == 403 or res.status_code == 521:
                page = self.__retry_method("requests", method, url)
                if page != "":
                    return page
                else:
                    return None
            else:
                return ""
        except requests.ConnectTimeout or requests.exceptions.ReadTimeout:
            page = self.__retry_method("requests", method, url)
            if page != "":
                return page
            else:
                return ""
        except requests.ConnectionError:
            page = self.__retry_method("requests", method, url)
            if page != "":
                return page
            else:
                return ""

    def urllib_request(self, method, url, data=None):
        content = ''
        try:
            if data is not None:
                request_data = urllib.parse.urlencode(data)
                http = urllib.request.Request(url, data=request_data, headers=self.__headers, method=method)
            else:
                http = urllib.request.Request(url, headers=self.__headers, method=method)
            req = urllib.request.urlopen(http)

            if req.status == 200:
                content = req.read()
                code = chardet.detect(content)["encoding"]
                if code is not None:

                    return str(content, encoding=code)
                else:
                    return str(content, encoding="utf-8")
            elif req.status == 403 or req.status == 404 or req.status == 500:
                page = self.__retry_method("urllib", method, url)
                if page != "":
                    return page
                else:
                    return None
            else:
                return ""
        except urllib.error.HTTPError:
            page = self.__retry_method("urllib", method, url)
            if page != "":
                return page
            else:
                return ""
        except urllib.error.URLError:
            page = self.__retry_method("urllib", method, url)
            if page != "":
                return page
            else:
                return ""
        except UnicodeDecodeError:
            return str(content, encoding="GB18030", errors='ignore')

    def urllib3_request(self, method, url, data=None):
        content = ''
        try:
            http = urllib3.PoolManager(timeout=self.timeout,
                                       retries=urllib3.Retry(self.retries, redirect=self.redirect))
            if data is not None:
                res = http.request_encode_body(method, url, fields=data, headers=self.__headers)
            elif self.param is not None:
                res = http.request_encode_url(method, url, fields=self.param, headers=self.__headers)
            else:
                res = http.request(method, url, headers=self.__headers, )
            if res.status == 200:
                content = res.data
                code = chardet.detect(content)["encoding"]
                if code is not None:
                    return str(content, encoding=code)
                else:
                    return str(content, encoding="utf-8")
            elif res.status == 403 or res.status == 404 or res.status == 500:
                page = self.__retry_method("urllib3", method, url)
                if page != "":
                    return page
                else:
                    return None
            else:
                return ""
        except urllib3.exceptions.ConnectionError:
            page = self.__retry_method("urllib3", method, url)
            if page != "":
                return page
            else:
                return ""
        except urllib3.exceptions.HTTPError:
            page = self.__retry_method("urllib3", method, url)
            if page != "":
                return page
            else:
                return ""
        except urllib3.exceptions.ConnectTimeoutError:
            page = self.__retry_method("urllib3", method, url)
            if page != "":
                return page
            else:
                return ""
        except urllib3.exceptions.RequestError:
            page = self.__retry_method("urllib3", method, url)
            if page != "":
                return page
            else:
                return ""
        except UnicodeDecodeError:
            return str(content, encoding="GB18030", errors='ignore')

    def __retry_method(self, old_method, method, url):
        sys.stdout.write("Retrying...")
        if old_method == "urllib":
            page = self.urllib3_request(method, url)
            if page is not None and page != "":
                return page
            elif page is None:
                if method == "POST":
                    return self.urllib3_request("GET", url)
                elif method == "GET":
                    return self.urllib3_request("POST", url)
                else:
                    return ""
            else:
                return ""
        elif old_method == "urllib3":
            page = self.requests_request(method, url)
            if page is not None and page != "":
                return page
            elif page is None:
                if method == "POST":
                    return self.requests_request("GET", url)
                elif method == "GET":
                    return self.requests_request("POST", url)
                else:
                    return ""
            else:
                return ""
        if old_method == "requests":
            page = self.urllib_request(method, url)
            if page is not None and page != "":
                return page
            elif page is None:
                if method == "POST":
                    return self.urllib_request("GET", url)
                elif method == "GET":
                    return self.urllib_request("POST", url)
                else:
                    return ""
            else:
                return ""

    @staticmethod
    def file_upload(path, url):
        file_size = os.path.getsize(path)
        file_name = os.path.split(path)[1]
        block_size = 10 * 1024 * 1024
        block_count = int(file_size / block_size)
        with open(path, "rb") as f:
            for index in range(block_count):
                if index == block_count - 1:
                    block_size = file_size - index * block_size
                block = f.read(block_size)
                blob = {
                    "name": file_name,
                    "index": index
                }
                response = requests.post(url, data=blob, files={"file": block})
                if response.status_code == 200:
                    print(response.text)
                else:
                    break

    @staticmethod
    def url_download(path, url, show_progress=True):
        start = round(time.time(), 2)

        def format_time(second):
            second = int(second)
            str_format = "{seconds}s".format(seconds=second)
            if second // 60 > 0:
                minutes = round(second // 60)
                seconds = second - minutes * 60
                str_format = "{minutes}m{seconds}s".format(minutes=minutes, seconds=seconds)
                if second // 3600 > 0:
                    hour = round(second // 3600)
                    minutes = round((second - hour * 3600) // 60)
                    seconds = second - minutes * 60 - hour * 3600
                    str_format = "{hour}h{minutes}m{seconds}s".format(hour=hour, minutes=minutes, seconds=seconds)
            return str_format

        def download_reporter(blob_nums, blob_size, file_size):
            per = 100.0 * blob_nums * blob_size / file_size
            if per > 100:
                per = 100
            already_use = round(time.time(), 2) - start
            predict_use = round(already_use / (blob_nums + 1) * (file_size / blob_size - blob_nums + 1), 2)
            speed = round(8 * (blob_nums + 1) / already_use, 2)
            speed_str = str(speed) + "KB/s"
            if speed // 1024 > 0:
                speed = round(speed / 1024, 2)
                speed_str = str(speed) + "MB/s"
            if show_progress:
                sys.stdout.write("\r" + "已下载：%.3f%%，已用时：%s，etc：%s，speed:%s" % (
                    per, format_time(already_use), format_time(predict_use), speed_str))
            del already_use, predict_use, speed, speed_str

        try:
            path = urllib.request.urlretrieve(url, path, reporthook=download_reporter)
            return path is not None
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(e)
            return HttpRequestBase.url_download(path, url, show_progress=False)
        except ValueError as e:
            print(e)
        except urllib.error.ContentTooShortError:
            return HttpRequestBase.url_download(path, url, show_progress=False)
