from datetime import datetime
import pandas as pd

class NseUrls:
    def __init__(self):
        self.__OPTION_CHAIN_BASE_URL = r"https://www1.nseindia.com/live_market/dynaContent/"\
                                     + r"live_watch/option_chain/optionKeys.jsp?symbol="
                                     
    def get_option_chain_url(self, symbol, expiry_date,dayfirst=False):
        try:
            expiry_date = self.__format_oc_expdate(expiry_date,dayfirst)
            complete_url =  self.__OPTION_CHAIN_BASE_URL + symbol + "&date=" + expiry_date
            return complete_url
        except Exception as err:
            raise Exception("Error occured while getting OC url, Error: ",str(err))

    def __format_oc_expdate(self,expiry_date,dayfirst=False):
        """string expirty_date to pandata datetime
        """
        try:
            date = pd.to_datetime(expiry_date,dayfirst=dayfirst)
            return date.strftime('%d%b%Y').upper()
        except Exception as err:
            raise Exception("Error occured while reading expiry date, Error: ",str(err))
    