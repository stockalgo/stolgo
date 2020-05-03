class NseUrls:
    def __init__(self):
        self.__OPTION_CHAIN_BASE_URL = r"https://www1.nseindia.com/live_market/dynaContent/"\
                                     + r"live_watch/option_chain/optionKeys.jsp?symbol="
                            
    def get_option_chain_url(self, symbol, expiry_date):
        complete_url =  self.__OPTION_CHAIN_BASE_URL + symbol + "&date=" + expiry_date
        return complete_url
