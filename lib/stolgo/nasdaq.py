import requests
import io

from datetime import timedelta
import pandas as pd

from stolgo.helper import get_date_range,get_formated_dateframe
from stolgo.request import RequestUrl,Curl

#default params for url connection
DEFAULT_TIMEOUT = 5 # seconds
MAX_RETRIES = 2
#default periods
DEFAULT_DAYS = 250

class NasdaqUrls:
    def __init__(self):
        self.STK_DATA_PRE_URL =  r"https://www.nasdaq.com/api/v1/historical/"
        self.date_formats = {"stock_data":"%Y-%m-%d"}

        #historical data header
        self.header = {
            "authority":"www.nasdaq.com",
            "method":"GET",
            "path":"/market-activity/stocks/aapl/historical",
            "scheme":"https",
            "accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-encoding":"gzip, deflate, br",
            "accept-language":"en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control":"max-age=0",
            "referer":"https://www.nasdaq.com/market-activity/quotes/historical",
            "sec-fetch-dest":"document",
            "sec-fetch-mode":"navigate",
            "sec-fetch-site":"same-origin",
            "sec-fetch-user":"?1",
            "upgrade-insecure-requests":"1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
            }

    def get_data_url(self,symbol,start,end):
        try:
            start =  start.strftime(self.date_formats["stock_data"])
            end = end.strftime(self.date_formats["stock_data"])
            url = self.STK_DATA_PRE_URL + symbol + r"/stocks/" + start + r"/" + end
            return url
        except Exception as err:
            raise Exception("Error occurred in URL constructions ", str(err))

class Nasdaq:
    """Nasdaq class to get data from nasdaq
    """
    def __init__(self,timeout=DEFAULT_TIMEOUT,max_retries=MAX_RETRIES,cloud_mode=False):
        if cloud_mode:
            self.requests = Curl(timeout,max_retries)
        else:
            self.requests = RequestUrl(timeout,max_retries)
        self.nasdaq_url =  NasdaqUrls()

    def __get_data_adjusted(self,dfs,symbol,start=None,end=None,periods=None):
        if periods and (dfs.shape[0] < periods):
            new_periods = periods - dfs.shape[0]
            try:
                s_from = e_till = None
                #if only start, find till today
                if start and (not end):
                    s_from = dfs.index[0] + timedelta(1)
                    e_till = None
                #if not start, can go to past
                elif((end and (not start)) or periods):
                    s_from = None
                    e_till = dfs.index[-1] - timedelta(1)
            except IndexError as err:
                raise Exception("Nasdaq Access error.")
            except Exception as exc:
                raise Exception("Nasdaq data error: ",str(exc))
            try:
                dfs_new = self.get_data(symbol,start = s_from,end = e_till,periods = new_periods)
                dfs = self.__join_dfs(dfs,dfs_new).sort_index(ascending=False)
            except Exception as exc:
                #Small part of data may not be available
                pass
        return dfs

    def __join_dfs(self,join,joiner):
        """will append joiner to join for oi_dfs

        :param join: df which will be appended
        :type join: pandas.DataFrame
        :param joiner: df which we want to append
        :type joiner: pandas.DataFrame
        :return: merged data frame
        :rtype: pandas.DataFrame
        """
        return join.append(joiner)

    def get_data(self,symbol,start=None,end=None,periods=None,dayfirst=False):
        """get_data API to fetch data from nasdaq

        :param symbol: stock symbol
        :type symbol: string
        :param start: start date, defaults to None
        :type start: string, optional
        :param end: end date, defaults to None
        :type end: string, optional
        :param periods: number of days, defaults to None
        :type periods: integer, optional
        :param dayfirst: True if date format is european style DD/MM/YYYY, defaults to False
        :type dayfirst: bool, optional
        :raises ValueError: for invalid inputs
        :raises Exception: incase if no data found
        :return: stock data
        :rtype: pandas.DataFrame
        """
        try:
            #Step1: get the date range
            s_from,e_till = get_date_range(start=start,end=end,periods=periods,dayfirst=dayfirst)

            if s_from > e_till:
                    raise ValueError("End should grater than start.")

            url = self.nasdaq_url.get_data_url(symbol=symbol,start=s_from,end=e_till)
            res = self.requests.get(url,headers=self.nasdaq_url.header)

            try:
                dfs = pd.read_csv(io.StringIO(res.content.decode('utf-8')))
            except Exception as err:
                #increase data range, nasdaq not returning for small set
                if e_till ==  get_formated_dateframe():
                    raise Exception("Nasdaq not retruning data for this date range.\
                                     Please, retry with other date ranges")
                e_till = get_formated_dateframe()
                if (e_till - s_from).days < DEFAULT_DAYS:
                    s_from = e_till - DEFAULT_DAYS
                dfs = self.get_data(symbol,start=s_from,end=e_till)

            dfs.set_index("Date",inplace=True)
            #convert to  datetime
            dfs.index = pd.to_datetime(dfs.index)
            dfs = self.__get_data_adjusted(dfs,symbol,start=start,end=end,periods=periods)
            return dfs
        except Exception as err:
            raise Exception("Error occurred while getting data :", str(err))