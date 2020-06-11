import subprocess

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

DEFAULT_TIMEOUT = 5 # seconds
MAX_RETRIES = 2

#class TimeoutHTTPAdapter credit : https://github.com/psf/requests/issues/3070#issuecomment-205070203
class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)

# If hitting curl with subprocess
class DummyResponse:
    def __init__(self,txt):
        self.text = None
        self.content = None
        if txt:
            try:
                self.text = txt.decode('utf-8')
            except UnicodeDecodeError:
                self.text = txt.reason.decode('iso-8859-1')
            self.content = txt
            self.status_code = 200
        else:
            raise Exception("Could not connect to host")

class Curl:
    def __init__(self,timeout=DEFAULT_TIMEOUT,max_retries=MAX_RETRIES):
        self.retry = max_retries
        self.timeout = timeout

    def __curl_cmd(self,url,headers):
        cmd = 'curl --connect-timeout ' + str(self.timeout) + ' --retry '+ str(self.retry) + ' "' + url + '" '
        query = " -H ".join(['"%s:%s"'%(key,value) for key,value in headers.items()])
        curl_cmd = cmd + "-H " + query + ' --compressed'
        return curl_cmd

    def get(self,url,headers):
        curl_cmd = self.__curl_cmd(url,headers)
        content = subprocess.Popen(curl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
        txt, _ = content.communicate()
        try:
            response= DummyResponse(txt)
            return response
        except Exception as err:
            raise Exception(str(err))


class RequestUrl:
    def __init__(self,timeout=DEFAULT_TIMEOUT,max_retries=MAX_RETRIES):
        self.session = self.get_session(timeout=timeout,max_retries=max_retries)


    def get_session(self,timeout=DEFAULT_TIMEOUT,max_retries=MAX_RETRIES):
        #backoff_factor allows us to change how long the processes will sleep between failed requests
        retries = Retry(
                    total=max_retries,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    )
        adapter = TimeoutHTTPAdapter(max_retries=retries ,timeout=timeout)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def get(self,*args,**kwargs):
        try:
            page = self.session.get(*args, **kwargs)
            # If the response was successful, no Exception will be raised
            page.raise_for_status()
            return page
        except requests.HTTPError as http_err:
            raise Exception("HTTP error occurred while fetching url :", str(http_err.response.content))

    def post(self,*args,**kwargs):
        try:
            page = self.session.post(*args, **kwargs)
            # If the response was successful, no Exception will be raised
            page.raise_for_status()
            return page
        except requests.HTTPError as http_err:
            raise Exception("HTTP error occurred while fetching url :", str(http_err.response.content))

