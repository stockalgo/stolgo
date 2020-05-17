import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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


class RequestUrl:
    def __init__(self,timeout=DEFAULT_TIMEOUT,max_retries=MAX_RETRIES):
        self.session = self.get_session(timeout=timeout,max_retries=max_retries)


    def get_session(self,timeout=DEFAULT_TIMEOUT,max_retries=MAX_RETRIES):
        retry = Retry(
                    total=max_retries,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    )
        adapter = TimeoutHTTPAdapter(max_retries=max_retries,timeout=timeout)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session
        
    def get(self,url,headers=None):
        try:
            page = self.session.get(url,headers=headers)
            # If the response was successful, no Exception will be raised
            page.raise_for_status()
            return page
        except requests.HTTPError as http_err:
            raise Exception("HTTP error occurred while fetching url :", str(http_err.response.content))