from datetime import date as dt
import pandas as pd
import requests
    
def get_formated_date(date=None,format=None,dayfirst=False):
    """string date to format date
    """
    try:
        if not date:
            date = dt.today()
        date_time = pd.to_datetime(date,dayfirst=dayfirst)
        if not format:
            format='%m/%d/%Y'
        return date_time.strftime(format)
            
    except Exception as err:
        raise Exception("Error occured while formatting date, Error: ",str(err))

def get_formated_dateframe(date=None,format=None,dayfirst=False):
    return pd.to_datetime(get_formated_date(date,format,dayfirst),format=format)
