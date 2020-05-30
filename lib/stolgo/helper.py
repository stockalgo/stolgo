from datetime import date as dt
import pandas as pd
import requests

#default periods
DEFAULT_DAYS = 250

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

def get_date_offset(periods=None,start=None,end=None,freq="B"):
    if start:
        if not periods:
            return get_formated_date()
        else:
            return pd.date_range(start=start,end=end,periods=periods,freq=freq)[-1]
    elif end:
       return pd.date_range(start=start,end=end,periods=periods,freq=freq)[0]
    else:
        raise ValueError("start/end , one should be None")

def get_date_range(start=None,end=None,periods=None,format=None,dayfirst=False,freq="B"):
    #Step 1: format date
    if start:
        start = get_formated_dateframe(start,dayfirst=dayfirst)
    if end:
        end = get_formated_dateframe(end,dayfirst=dayfirst)

    #Step 2: date range with peroids
    if (not periods) and (not start):
        periods = DEFAULT_DAYS
    #if only start, find till today
    if start and (not end):
        s_from = start
        e_till = get_date_offset(start=start,periods=periods)#s_from + pd.offsets.BDay(periods)
    #if not start, go to past
    elif(end and (not start)):
        s_from = get_date_offset(end=end,periods=periods)#e_till - pd.offsets.BDay(periods)
        e_till = end
    #if start and end, no need to change
    elif(start and end):
        s_from = start
        e_till = end
    # if no stat/end and periods given, we get last 1 years of data
    else:
        s_from = get_date_offset(end=end,periods=periods,freq=freq)
        e_till = get_formated_dateframe()

    #Step 3: Format to input date format
    s_from = get_formated_dateframe(date=s_from,format=format)
    e_till = get_formated_dateframe(date=e_till,format=format)

    return s_from,e_till