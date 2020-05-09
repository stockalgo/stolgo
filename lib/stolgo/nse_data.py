import os
import requests

from datetime import datetime
import pandas as pd
from pandas import ExcelWriter
from requests.exceptions import HTTPError

from stolgo.nse_urls import NseUrls

class NseData:
    def __init__(self):
        self.__nse_urls = NseUrls()
        self.__headers = {'User-Agent': "Mozilla/5.0"}
    
    def get_option_chain_df(self, symbol, expiry_date,dayfirst=False):
        """ This fucntion fetches option chain data and returns 
            in the form of pandas data frame

        Arguments:
            symbol {[string]} -- [stock symbol]
            expiry_date {[string]} -- [expiry date]
            dayfirst{[bool]} -- [to consider date first, european style DD/MM/YYYY]
        """
        try:
            oc_url = self.__nse_urls.get_option_chain_url(symbol, expiry_date,dayfirst)
            oc_page = requests.get(oc_url, headers = self.__headers)
            # If the response was successful, no Exception will be raised
            oc_page.raise_for_status()
            
        except HTTPError as http_err:
            raise Exception("HTTP error occurred while fetching nse url :", str(http_err))
        except Exception as err:
             raise Exception("something went wrong :", str(err))
        else:
            try:
                dfs = pd.read_html(oc_page.text)
                return dfs[1]
            except Exception as err:
                raise Exception("Error occured while reading html :", str(err))
    
    def __get_file_path(self, file_name, file_path = None, is_use_default_name = True):
        try:
            if not file_path:
                file_path = os.getcwd()
            
            if os.path.isfile(file_path):
                if (not is_use_default_name):
                    return file_path
                # if need to use default file path, we get parent path
                else:
                    file_path = os.path.dirname(file_path)
                    
            # datetime object containing current date and time
            now = datetime.now()
            # dd/mm/YY H:M:S
            dt_string = now.strftime("%d_%B_%H_%M")
            file_name = file_name + "_" + dt_string + ".xlsx"
            
            excel_path = os.path.join(file_path, file_name)
            return excel_path
        except Exception as err:
            print("Error while naming file. Error: ", str(err))
    
    def get_option_chain_excel(self, symbol, expiry_date,dayfirst=False,file_path = None, is_use_default_name = True):
        """This fucntion fetches option chain data and returns 
            in the form of excel (.xlsx)
        Arguments:
            symbol {[string]} -- [stock symbol]
            expiry_date {[string]} -- [expiry date]
            dayfirst{[bool]} -- [to consider date first, european style DD/MM/YYYY]
            
        Keyword Arguments:
            file_path {[string]} -- [filepath or folder path] (default: {None})
            is_use_default_name {bool} -- [to set file name ] (default: {True})
        """
        try:
            df = self.get_option_chain_df(symbol, expiry_date,dayfirst)
            file_name = symbol + "_" + expiry_date 
            excel_path = self.__get_file_path(file_name, file_path, is_use_default_name)
            
            writer = ExcelWriter(excel_path)
            df.to_excel(writer, file_name)
            writer.save()
        except Exception as err:
            raise Exception("Error occured while getting excel :", str(err))