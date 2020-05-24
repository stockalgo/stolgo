from datetime import datetime,date
import pandas as pd

from stolgo.helper import get_formated_date,get_date_range

class NseUrls:
    def __init__(self):
        self.__OPTION_CHAIN_BASE_URL = r"https://www1.nseindia.com/live_market/dynaContent/"\
                                     + r"live_watch/option_chain/optionKeys.jsp?symbol="
        #In EnocodedURI
        self.__PARTICIPANT_OI_PRE_URL = r"https://www.nseindia.com/api/reports?archives=%5B%7B%22name"\
                                    + r"%22%3A%22F%26O%20-%20Participant%20wise%20Trading%20Volumes(csv)"\
                                    + r"%22%2C%22type%22%3A%22archives%22%2C%22category%22%3A%22derivatives"\
                                    + r"%22%2C%22section%22%3A%22equity%22%7D%5D&date="
        self.__PARTICIPANT_OI_POST_URL = r"&type=equity&mode=single"

        #Dictionary contains nse date formats for urls
        self.nse_date_formats = {
                                    "opt_chain":'%d%b%Y',
                                    "part_oi":'%d-%b-%Y',
                                    "stock_data":'%d-%m-%Y',
                                    "index_data":'%d-%m-%Y',
                                    "vix_data":'%d-%b-%Y'
                                }

        #browser like header to avoid error 403
        self.header = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
        #paticipant wise OI
        self.PART_OI_CLM = ['Future Index Long', 'Future Index Short', 'Future Stock Long',
                            'Future Stock Short\t', 'Option Index Call Long',
                            'Option Index Put Long', 'Option Index Call Short',
                            'Option Index Put Short', 'Option Stock Call Long',
                            'Option Stock Put Long', 'Option Stock Call Short',
                            'Option Stock Put Short', 'Total Long Contracts\t',
                            'Total Short Contracts']

        #stock data
        self.__HIST_DATA_PRE_URL = r"https://www.nseindia.com/api/historical/cm/equity?symbol="

        #Historical index data URL
        self.INDEX_URL = r"https://www1.nseindia.com/products/content/equities/indices/historical_index_data.htm"
        self.__HIST_INDEX_DATA_URL = r"https://www1.nseindia.com/products/dynaContent/equities/indices/historicalindices.jsp?indexType="
        self.__HIST_VIX_DATA_URL = r"https://www1.nseindia.com/products/dynaContent/equities/indices/hist_vix_data.jsp?&fromDate="
        self.INDEX_DATA_CLM = ["Date","Open","High","Low","Close","Shares Traded","Turnover( Rs. Cr)"]
        self.VIX_DATA_CLM = ["Date","Open","High","Low","Close","Prev. Close","Change","% Change"]

    def get_option_chain_url(self,symbol,expiry_date=None,dayfirst=False):
        try:
            if expiry_date:
                expiry_date = get_formated_date(expiry_date,self.nse_date_formats["opt_chain"],dayfirst).upper()
                complete_url =  self.__OPTION_CHAIN_BASE_URL + symbol + "&date=" + expiry_date
                return complete_url
            else:
                return self.__OPTION_CHAIN_BASE_URL + symbol
        except Exception as err:
            raise Exception("Error occured while getting OC url, Error: ",str(err))

    def get_participant_oi_url(self,date,dayfirst=False):
        try:
            date = get_formated_date(date,format=self.nse_date_formats["part_oi"],dayfirst=dayfirst)
            url = self.__PARTICIPANT_OI_PRE_URL + date + self.__PARTICIPANT_OI_POST_URL
            return url
        except Exception as err:
            raise Exception("Error occured while getting participant OI. ", str(err))

    def get_stock_data_url(self,symbol,series="EQ",start=None,end=None,periods=None,dayfirst=False):
        try:
            #Step1: get the date range
            s_from = get_date_range(start=start,end=end,periods=periods,dayfirst=dayfirst)["start"]
            e_till = get_date_range(start=start,end=end,periods=periods,dayfirst=dayfirst)["end"]

            #Step2: Build url
            url = None
            if "INDIA VIX" == symbol:
                s_from = s_from.strftime(self.nse_date_formats["vix_data"])
                e_till = e_till.strftime(self.nse_date_formats["vix_data"])
                url = self.__HIST_VIX_DATA_URL + s_from + "&toDate=" + e_till
            else:
                #time format is same for index data and nifty data
                s_from = s_from.strftime(self.nse_date_formats["stock_data"])
                e_till = e_till.strftime(self.nse_date_formats["stock_data"])

                if "NIFTY" in symbol:
                    symbol = symbol.replace(' ',"%20").upper()
                    url = self.__HIST_INDEX_DATA_URL + symbol + "&fromDate=" +\
                            s_from + "&toDate=" + e_till
                else:
                    url = self.__HIST_DATA_PRE_URL + symbol + r"&series=[%22" + series+\
                        r"%22]&from=" + s_from + r"&to=" + e_till + r"&csv=true"
            return url

        except Exception as err:
            raise Exception("Error occurred while getting stock data URL. ", str(err))