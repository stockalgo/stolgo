import requests
import json
from datetime import datetime,date
import pandas as pd

from stolgo.helper import get_formated_date,get_date_range,is_ind_index,get_data_resample
from stolgo.request import RequestUrl

#default params for url connection
DEFAULT_TIMEOUT = 5 # seconds
MAX_RETRIES = 2

class SamcoUrl:
    def __init__(self):
        #token needs to be set by user application
        self.DATA_HEADER = {
                            'Accept': 'application/json',
                            'x-session-token': None
                            }
        self.LOGIN_HEADERS =  {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                        }
        self.LOGIN_URL = "https://api.stocknote.com/login"

        #historical data url
        self.HIST_INDEX_URL = "https://api.stocknote.com/history/indexCandleData?indexName="
        self.HIST_STK_URL = "https://api.stocknote.com/history/candleData?symbolName="

        #intraday data
        self.INTRA_INDEX_URL = "https://api.stocknote.com/intraday/indexCandleData?indexName="
        self.INTRA_STK_URL = "https://api.stocknote.com/intraday/candleData?symbolName="

        self.date_format = {
                            "HIST":"%Y-%m-%d",
                            "INTRA":"%Y-%m-%d %H:%M:%S"
                            }

    def set_session(self,token):
        self.DATA_HEADER = {
                        'Accept': 'application/json',
                        'x-session-token': token
                        }

    def __build_url(self,symbol,start,end,url,date_format):
        symbol = symbol.upper().replace(" ","%20")
        start = start.strftime(date_format).replace(" ","%20").replace(":","%3A")
        end = end.strftime(date_format).replace(" ","%20").replace(":","%3A")
        url_build = url + symbol + "&fromDate=" + start + "&toDate=" + end
        return url_build

    def get_intra_data_url(self,symbol,start,end):
        try:
            url = None
            if is_ind_index(symbol):
                url = self.__build_url(symbol,start,end,self.INTRA_INDEX_URL,self.date_format["INTRA"])
            else:
                url = self.__build_url(symbol,start,end,self.INTRA_STK_URL,self.date_format["INTRA"])
            return url
        except Exception as err:
            raise Exception("Error occurred while getting stock data URL. ", str(err))

    def get_hist_data_url(self,symbol,start,end):
        try:
            url = None
            if is_ind_index(symbol):
                url = self.__build_url(symbol,start,end,self.HIST_INDEX_URL,self.date_format["HIST"])
            else:
                url = self.__build_url(symbol,start,end,self.HIST_STK_URL,self.date_format["HIST"])
            return url
        except Exception as err:
            raise Exception("Error occurred while getting stock data URL. ", str(err))


class Samco:
    def __init__(self,user_id,password,yob,timeout=DEFAULT_TIMEOUT,max_retries=MAX_RETRIES):
        #internal initialization
        self.__request = RequestUrl(timeout,max_retries)
        self.urls = SamcoUrl()

        request_body = {
                        "userId": user_id,
                        "password": password,
                        "yob": yob
                        }

        #lets login
        res = self.__request.post(self.urls.LOGIN_URL,
                            data=json.dumps(request_body),
                            headers = self.urls.LOGIN_HEADERS, verify=False)

        self.login_res = json.loads(res.text)
        #set token
        self.urls.set_session(self.login_res.get("sessionToken"))

    def __get_hist_data(self,symbol,start,end,interval="1D"):
        try:
            url = self.urls.get_hist_data_url(symbol,start,end)
            res = self.__request.get(url,headers=self.urls.DATA_HEADER)
            json_key = "historicalCandleData"
            if is_ind_index(symbol):
                json_key = "indexCandleData"
            hist_data_dict =  json.loads(res.text).get(json_key)
            dfs = pd.json_normalize(hist_data_dict)
            dfs.set_index("date",inplace=True)
            # Converting the index as date
            dfs.index = pd.to_datetime(dfs.index)
            return dfs

        except Exception as err:
            raise Exception("Error occurred for historical data: ",str(err))

    def __get_intra_data(self,symbol,start,end,interval="1M"):
        try:
            url = self.urls.get_intra_data_url(symbol,start,end)
            res = self.__request.get(url,headers=self.urls.DATA_HEADER)
            json_key = "intradayCandleData"
            if is_ind_index(symbol):
                json_key = "indexIntraDayCandleData"
            intra_data =  json.loads(res.text).get(json_key)
            dfs = pd.DataFrame(intra_data)
            dfs.set_index("dateTime",inplace=True)
            # Converting the index as date
            dfs.index = pd.to_datetime(dfs.index)
            return dfs
        except Exception as err:
            raise Exception("Error occurred for historical data: ",str(err))

    def __finetune_df(self,df):
        """drop dataframe out of range time

        :param df: input dataframe
        :type df: pd.DataFrame
        """
        drop_index = (df.between_time("07:00","09:00",include_end=False) + \
                        df.between_time("15:30","17:00",include_start=False)).index
        df.drop(drop_index,inplace=True)

    def get_data(self,symbol,start=None,end=None,periods=None,interval="1D",dayfirst=False):
        """Samco getData API for intraday/Historical data

        :param symbol: stock symbol
        :type symbol: string
        :param start: start time, defaults to None
        :type start: string optional
        :param end: end time, defaults to None
        :type end: string, optional
        :param periods: No of days, defaults to None
        :type periods: integer, optional
        :param interval: timeframe, defaults to "1D"
        :type interval: string, optional
        :param dayfirst: if date in european style, defaults to False
        :type dayfirst: bool, optional
        :raises ValueError: invalid time
        :raises Exception: for execption
        :return: data requested
        :rtype: pandas.DataFrame
        """
        try:
            s_from,e_till = get_date_range(start=start,end=end,periods=periods,dayfirst=dayfirst)
            if s_from > e_till:
                raise ValueError("End should grater than start.")

            #capitalize
            symbol = symbol.upper()
            interval = interval.upper()

            time_frame  = pd.Timedelta(interval)
            #if interval is 1 day, Use historical data API
            day_time_frame = pd.Timedelta("1D")
            min_time_frame = pd.Timedelta("1M")
            if time_frame >= day_time_frame:
                dfs = self.__get_hist_data(symbol,s_from,e_till)
                dfs = dfs.apply(pd.to_numeric)
                if time_frame != day_time_frame:
                    dfs = get_data_resample(dfs,interval)
            else:
                dfs = self.__get_intra_data(symbol,s_from,e_till)
                dfs = dfs.apply(pd.to_numeric)
                if time_frame != min_time_frame:
                    dfs = get_data_resample(dfs,interval)

            if not dfs.empty:
                return dfs

        except Exception as err:
            raise Exception("Error occurred while fetching data :", str(err))