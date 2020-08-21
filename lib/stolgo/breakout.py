import pandas as pd
from stolgo.exception import BadDataError

class Breakout:
    def __init__(self,periods=13,percentage=2):
        self.periods = periods
        self.percentage = percentage

    def is_consolidating(self,dfs,periods=None,percentage=None):
        """Check if price in consolidating in range for given periods

        :param dfs: input candles
        :type dfs: pandas dataframe
        :param periods: Number of candles, defaults to None
        :type periods: integer, optional
        :param percentage: range of consolidation in percentage, defaults to None
        :type percentage: float, optional
        :raises BadDataError: data error
        :return: is_consolidating
        :rtype: bool
        """
        try:
            if not periods:
                periods = self.periods
            if not percentage:
                percentage = self.percentage

            if dfs.shape[0] < periods:
                raise BadDataError("Data is not enough for this periods")
            recent_dfs = dfs[-1*periods:]
            max_close = recent_dfs['Close'].max()
            min_close = recent_dfs['Close'].min()
            max_adjust = 1-(percentage/100)
            if(min_close > max_close * max_adjust):
                return True
            return False
        except Exception as err:
            raise Exception(str(err))

    def is_breaking_out(self,dfs,periods=None,percentage=None):
        """check if last candle is breaking out or not

        :param dfs: input candles
        :type dfs: pandas dataframe
        :param periods: Number of candles, defaults to None
        :type periods: integer, optional
        :param percentage: range of consolidation in percentage,, defaults to None
        :type percentage: float, optional
        :raises Exception: data error
        :return: is_breaking_out
        :rtype: bool
        """
        try:
            if(self.is_consolidating(dfs[:-1],periods,percentage)):
                last_close = dfs[-1:]
                recent_dfs = dfs[-1*periods:-1]
                if(recent_dfs['Close'].max()<last_close['Close'].values[0]):
                    return True
            return False
        except Exception as err:
            raise Exception(str(err))

    def is_breaking_down(self,dfs,periods=None,percentage=None):
        """check if last candle is breaking down or not

        :param dfs: input candles
        :type dfs: pandas dataframe
        :param periods: Number of candles, defaults to None
        :type periods: integer, optional
        :param percentage: range of consolidation in percentage,, defaults to None
        :type percentage: float, optional
        :raises Exception: data error
        :return: is_breaking_down
        :rtype: bool
        """
        try:
            if(self.is_consolidating(dfs[:-1],periods,percentage)):
                last_close = dfs[-1:]
                recent_dfs = dfs[-1*periods:-1]
                if(recent_dfs['Close'].min()>last_close['Close'].values[0]):
                    return True
            return False
        except Exception as err:
            raise Exception(str(err))

