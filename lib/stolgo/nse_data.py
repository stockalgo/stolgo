import os
import requests
import concurrent.futures
import threading
import io

from datetime import datetime,timedelta
import pandas as pd
from pandas import ExcelWriter
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup

from stolgo.nse_urls import NseUrls
from stolgo.helper import get_formated_date
from stolgo.request import RequestUrl

#default params for url connection 
DEFAULT_TIMEOUT = 5 # seconds
MAX_RETRIES = 2

class NseData:
    def __init__(self,timeout=DEFAULT_TIMEOUT,max_retries=MAX_RETRIES):
        self.__nse_urls = NseUrls()
        self.__headers = self.__nse_urls.header
        #create request
        self.__request = RequestUrl()

    def get_oc_exp_dates(self,symbol):
        """get current  available expiry dates

        Arguments:
            symbol {[string]} -- symbol name
        """
        try:
            base_oc_url = self.__nse_urls.get_option_chain_url(symbol)
            page = self.__request.get(base_oc_url,headers=self.__headers)
            soup = BeautifulSoup(page.text,'lxml')
            table = soup.find("select",{"id":"date"})
            expiry_out = table.find_all("option")
            expiry_dates = [exp_date.get("value") for exp_date in expiry_out][1:]
            return expiry_dates

        except Exception as err:
            raise Exception("something went wrong while reading nse URL :", str(err))

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
            # If the response was successful, no Exception will be raised
            oc_page = self.__request.get(oc_url, headers = self.__headers)

        except Exception as err:
             raise Exception("Error occured while connecting NSE :", str(err))
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
    
    def __join_part_oi_dfs(self,df_join,df_joiner):
        """ will append joiner to join

        Arguments:
            df_join {[dict]} -- [Dictionary of participants]
            df_joiner {[dict]} -- [Dictionary of participants]
        """
        for client in df_join:
            df_join[client] = self.__join_dfs(df_join[client],df_joiner[client]).sort_index()
    
    def __join_dfs(self,join,joiner):
        """will append joiner to join

        Arguments:
            join {[dataframe]} -- [will get appended]
            joiner {[dataframe]} -- [df which will be appended in join df]
        """
        return join.append(joiner)

    def get_part_oi_df(self,start=None,end=None,periods=None,dayfirst=False,workers=None):
        """Return dictionary of participants containing data frames

        Keyword Arguments:
            start {[string]} -- [start time ] (default: {None})
            end {[string]} -- [end time] (default: {None})
            periods {[interger]} -- [number of days] (default: {None})
            dayfirst {bool} -- [True if date in DD/MM/YYY format] (default: {False})
            workers {[integer]} -- [Number of threads for requesting nse] (default: {None})

        Returns:
            [dictionary] -- [dict of participants containing dataframes]
        """
        try:
            #format date just in case
            if start:
                start = get_formated_date(start,dayfirst=dayfirst)
            if end:
                end = get_formated_date(end,dayfirst=dayfirst)
            
            #get urls for these days
            dates = pd.date_range(start=start,end=end, periods=periods,freq='B')
            url_date = [(self.__nse_urls.get_participant_oi_url(date),date) for date in dates]#
            
            oi_clm = self.__nse_urls.part_oi_clm
            #lets preinitialize, better readability
            oi_dfs = {  "Client":pd.DataFrame(columns=oi_clm,index=dates),
                        "DII":pd.DataFrame(columns=oi_clm,index=dates),
                        "FII":pd.DataFrame(columns=oi_clm,index=dates),
                        "Pro":pd.DataFrame(columns=oi_clm,index=dates),
                        "TOTAL":pd.DataFrame(columns=oi_clm,index=dates)
                        }
            
            if not workers:
                workers = os.cpu_count() * 2
            
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                responses = {executor.submit(self.__request.get, url,self.__headers): (url,date) for url,date in url_date}
                for res in concurrent.futures.as_completed(responses):
                    url,date = responses[res]
                    try:
                        csv = res.result()
                    except Exception as exc:
                        #might be holiday
                        pass
                    else:
                        df = pd.read_csv(io.StringIO(csv.content.decode('utf-8')))
                        #drop the first header
                        df_header = df.iloc[0]
                        #is there any implace way?
                        df = df[1:]
                        df.columns = df_header
                        df.set_index('Client Type',inplace=True)
                        #lets us create data frome for all client type
                        oi_dfs['Client'].loc[date] = df.loc['Client']
                        oi_dfs['FII'].loc[date] = df.loc['FII']
                        oi_dfs['DII'].loc[date] = df.loc['DII']
                        oi_dfs['Pro'].loc[date] = df.loc['Pro']
                        oi_dfs['TOTAL'].loc[date] = df.loc['TOTAL']
            
            if not oi_dfs['Client'].empty:
                #remove nan row
                for client in oi_dfs:
                    oi_dfs[client].dropna(inplace=True)
                
                #if holiday occured in business day, lets retrive more data equivalent to holdidays. 
                if oi_dfs['Client'].shape[0] < periods:
                    new_periods = periods - oi_dfs['Client'].shape[0]
                    try:
                        #if only start, find till today 
                        if start and (not end):
                            s_from = oi_dfs['Client'].index[-1] + timedelta(1)
                            e_till = None
                        #if not start, can go to past
                        elif(end and (not start)):
                            s_from = None
                            e_till = oi_dfs['Client'].index[0] - timedelta(1)
                        #if start and end, no need to change
                        else:
                            return oi_dfs
                    except IndexError as err:
                        raise Exception("NSE Access error.size down/clean cookies to resolve the issue.")
                    except Exception as exc:
                        raise Exception("participant OI error: ",str(exc))

                    oi_dfs_new = self.get_part_oi_df(start = s_from,end = e_till,periods = new_periods)
                    self.__join_part_oi_dfs(oi_dfs,oi_dfs_new)
                
                return oi_dfs

        except Exception as err:
            raise Exception("Error occured while getting part_oi :", str(err))

    def get_data(self,symbol,series="EQ",start=None,end=None,periods=None,dayfirst=False):
        """get_data API retuns stock data

        Arguments:
            symbol {[string]} -- [stock symbol as per nse]

        Keyword Arguments:
            series {str} -- [segment type] (default: {"EQ"})
            start {[string]} -- [start date] (default: {None})
            end {[string]} -- [end date] (default: {None})
            periods {[integer]} -- [number of days] (default: {None})
            dayfirst {bool} -- [True if date in DD/MM/YYY format, date first then month] (default: {False})
        """
        try:
            data_url = self.__nse_urls.get_stock_data_url\
                                                        (
                                                        symbol.upper(),series=series,start=start,
                                                        end=end,periods=periods,dayfirst=dayfirst
                                                        )

            csv = self.__request.get(data_url,headers=self.__headers)
            dfs = pd.read_csv(io.StringIO(csv.content.decode('utf-8')))
            dfs.set_index('Date ',inplace=True)
            # Converting the index as date
            dfs.index = pd.to_datetime(dfs.index)

            if dfs.shape[0] < periods:
                new_periods = periods - dfs.shape[0]
                try:
                    #if only start, find till today 
                    if start and (not end):
                        s_from = dfs.index[0] + timedelta(1)
                        e_till = None
                    #if not start, can go to past
                    elif(end and (not start)):
                        s_from = None
                        e_till = dfs.index[-1] - timedelta(1)
                    #if start and end, no need to change
                    else:
                        return dfs
                except IndexError as err:
                    raise Exception("NSE Access error.")
                except Exception as exc:
                    raise Exception("Stock data error: ",str(exc))
                dfs_new = self.get_data(symbol,series,start = s_from,end = e_till,periods = new_periods)
                dfs = self.__join_dfs(dfs,dfs_new).sort_index(ascending=False)
                
            return dfs

        except Exception as err:
            raise Exception("Error occured while stock data :", str(err))