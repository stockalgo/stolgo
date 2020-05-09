from datetime import datetime
import pandas as pd

from stolgo.helper import get_formated_date

class NseUrls:
    def __init__(self):
        self.__OPTION_CHAIN_BASE_URL = r"https://www1.nseindia.com/live_market/dynaContent/"\
                                     + r"live_watch/option_chain/optionKeys.jsp?symbol="
                                     
        #Dictionary contains nse date formats for urls
        self.nse_date_formats = {
                                    "opt_chain":'%d%b%Y',
                                    "part_oi":'%d-%b-%Y'
                                } 
                                     
    def get_option_chain_url(self, symbol, expiry_date=None,dayfirst=False):
        try:
            if expiry_date:
                expiry_date = get_formated_date(expiry_date,self.nse_date_formats["opt_chain"],dayfirst).upper()
                complete_url =  self.__OPTION_CHAIN_BASE_URL + symbol + "&date=" + expiry_date
                return complete_url
            else:
                return self.__OPTION_CHAIN_BASE_URL + symbol
        except Exception as err:
            raise Exception("Error occured while getting OC url, Error: ",str(err))