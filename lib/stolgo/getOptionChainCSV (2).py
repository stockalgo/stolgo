import requests
from pandas import ExcelWriter
import pandas as pd
from datetime import datetime
import os
from bs4 import BeautifulSoup

class optionChain:

    def __init__(self):
        self.PARTIALBASEURL = "https://www1.nseindia.com/live_market/dynaContent/live_watch/option_chain/optionKeys.jsp?symbol=" 
        self.headers = {'User-Agent': "Mozilla/5.0"}

    def __getDumpFileName(self,name,folderPath=None):
        try:
            if not folderPath:
                folderPath = os.getcwd()

            if not os.path.exists(folderPath):
                os.makedirs(folderPath)

            #Get file Path
            # datetime object containing current date and time
            now = datetime.now()
            # dd/mm/YY H:M:S
            dtString = now.strftime("%d_%B_%H_%M")
            fileName = name+"_"+dtString+".xlsx"
            excelFilePath = os.path.join(folderPath,fileName)
            return excelFilePath
        except Exception as err:
            print("Error while naming file. Error: ",str(err))

    def __request_url(self,url,headers):
        page = requests.get(url,headers=headers)
        if 200 is page.status_code:
            return page
        else:
            raise Exception("HTTP error occurred while fetching url")
        
    def getOptionChain(self,symbol,date=None,folderPath=None):
        try:
            
            if date:
                partialBaseUrl  = self.PARTIALBASEURL+ symbol + "&date=" + date
            else:
                page = self.__request_url(self.PARTIALBASEURL,self.headers)
                soup = BeautifulSoup(page.text,'lxml')
                table = soup.find("select",{"id":"date"})
                expiry_dates = table.find_all("option")
                expiry_date = [exp_date.get("value") for exp_date in expiry_dates][1]
                partialBaseUrl  = self.PARTIALBASEURL + symbol + "&date=" + expdate
            
            page = self.__request_url(self.PARTIALBASEURL,self.headers)
            dfs =pd.read_html(page.text)
            excelFilePath = self.__getDumpFileName(symbol+"_"+expdate)
            #dfs[1] = dfs[1].loc[:, ~dfs[1].columns.str.contains('^Unnamed')]
            writer = ExcelWriter(excelFilePath)
            dfs[1].to_excel(writer,symbol+"_"+expdate)
            writer.save()
            #print(dfs)
        
        except Exception as err:
            print("Error occured while hitting nse option chain page. Error: ",str(err))


def main():
    testOC = optionChain()
    strike_list  = testOC.getOptionChain('BANKNIFTY')
    

  
if __name__== "__main__":
  main()