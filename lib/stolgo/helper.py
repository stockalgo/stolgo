import datetime
import pandas as pd
import requests

def get_past_dates(num_days,date_format):
    base = datetime.datetime.today()
    date_list = [(base - datetime.timedelta(days=x)).strftime(date_format) for x in range(num_days)]
    return date_list
    
def get_formated_date(date,format=None,dayfirst=False):
    """string date to format date
    """
    try:
        date_time = pd.to_datetime(date,dayfirst=dayfirst)
        if not format:
            format='%m/%d/%Y'
        return date_time.strftime(format)
            
    except Exception as err:
        raise Exception("Error occured while formatting date, Error: ",str(err))