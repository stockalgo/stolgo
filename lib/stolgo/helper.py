import datetime
import pandas as pd
import requests

def get_past_dates(num_days,date_format):
    base = datetime.datetime.today()
    date_list = [(base - datetime.timedelta(days=x)).strftime(date_format) for x in range(num_days)]
    return date_list
    
def get_formated_date(date,format,dayfirst=False):
    """string date to format date
    """
    try:
        date_time = pd.to_datetime(date,dayfirst=dayfirst)
        return date_time.strftime(format)
    except Exception as err:
        raise Exception("Error occured while formatting date, Error: ",str(err))

def request_url(url,headers):
    try:
        page = requests.get(url,headers=headers)
        # If the response was successful, no Exception will be raised
        page.raise_for_status()
        return page
    except HTTPError as http_err:
        raise Exception("HTTP error occurred while fetching url :", str(http_err))