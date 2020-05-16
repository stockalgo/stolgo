from datetime import datetime,date
import pandas as pd

from stolgo.helper import get_formated_date,get_formated_dateframe

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
                                    "stock_data":'%d-%m-%Y'
                                }

        #browser like header to avoid error 403
        self.header = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
        #paticipant wise OI
        self.part_oi_clm = ['Future Index Long', 'Future Index Short', 'Future Stock Long',
                            'Future Stock Short\t', 'Option Index Call Long',
                            'Option Index Put Long', 'Option Index Call Short',
                            'Option Index Put Short', 'Option Stock Call Long',
                            'Option Stock Put Long', 'Option Stock Call Short',
                            'Option Stock Put Short', 'Total Long Contracts\t',
                            'Total Short Contracts']
        
        #stock data
        self.__HIST_DATA_PRE_URL = r"https://www.nseindia.com/api/historical/cm/equity?symbol="
                                     
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

            #Step 1: format date 
            if start:
                start = get_formated_dateframe(start,format=self.nse_date_formats["stock_data"],dayfirst=dayfirst)
            if end:
                end = get_formated_dateframe(end,format=self.nse_date_formats["stock_data"],dayfirst=dayfirst)
            
            #Step 2: date range with peroids
            #if only start, find till today 
            if start and (not end):
                s_from = start
                if periods:
                    e_till = s_from + pd.offsets.BDay(periods)
                else:
                    e_till = get_formated_dateframe(format=self.nse_date_formats["stock_data"])
            #if not start, can go to past
            elif(end and (not start)):
                e_till = end
                if periods:
                    s_from = e_till - pd.offsets.BDay(periods)
                else:
                    # last one year data
                    s_from = e_till - pd.offsets.BDay(255)
            #if start and end, no need to change
            elif(start and end):
                s_from = start
                e_till = end
            # if no stat/end and periods given, we get past data of periods
            else:
                e_till = get_formated_dateframe(format=self.nse_date_formats["stock_data"])
                if(periods):
                    s_from = e_till - pd.offsets.BDay(periods)
                else:
                    # last one year data
                    s_from = e_till - pd.offsets.BDay(255)

            #step3: Build url
            s_from = s_from.strftime(self.nse_date_formats["stock_data"])
            e_till = e_till.strftime(self.nse_date_formats["stock_data"])
            url = self.__HIST_DATA_PRE_URL + symbol + r"&series=[%22" + series+\
                    r"%22]&from=" + s_from + r"&to=" + e_till + r"&csv=true"
            return url

        except Exception as err:
            raise Exception("Error occured while getting stock data URL. ", str(err))