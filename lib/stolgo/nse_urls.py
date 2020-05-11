from datetime import datetime
import pandas as pd

from stolgo.helper import get_formated_date

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
                                    "part_oi":'%d-%b-%Y'
                                }
        
        #paticipant wise OI
        self.part_oi_clm = ['Future Index Long', 'Future Index Short', 'Future Stock Long',
                            'Future Stock Short\t', 'Option Index Call Long',
                            'Option Index Put Long', 'Option Index Call Short',
                            'Option Index Put Short', 'Option Stock Call Long',
                            'Option Stock Put Long', 'Option Stock Call Short',
                            'Option Stock Put Short', 'Total Long Contracts\t',
                            'Total Short Contracts']
                                     
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
        
    def get_participant_oi_url(self,date,dayfirst=False):
        try:
            date = get_formated_date(date, self.nse_date_formats["part_oi"],dayfirst)
            url = self.__PARTICIPANT_OI_PRE_URL + date + self.__PARTICIPANT_OI_POST_URL
            return url
        except Exception as err:
            raise Exception("Error occured ehilr getting participant OI. ", str(err))
    