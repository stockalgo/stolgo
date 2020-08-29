import pandas as pd
import sys
from stolgo.exception import BadDataError

class Trend:
    def __init__(self,periods=13,percentage=2):
        self.periods = periods
        self.percentage = percentage

    def is_giant_uptrend(self,dfs,periods=None,percentage=None):
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
            prev_candle = None
            for candle in recent_dfs.iterrows():
                #check if the candle is green
                if(candle[1]["Close"] < candle[1]["Open"]):
                    return False
                if(not prev_candle):
                    prev_candle = candle
                    continue
                if(prev_candle[1]["Close"] > candle[1]["Close"]):
                    return False
            return True
        except Exception as err:
            raise Exception(str(err))

    def is_giant_downtrend(self,dfs,periods=None,percentage=None):
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
            prev_candle = None
            for candle in recent_dfs.iterrows():
                #check if the candle is red
                if(candle[1]["Close"] > candle[1]["Open"]):
                    return False
                if(not prev_candle):
                    prev_candle = candle
                    continue
                if(prev_candle[1]["Close"] < candle[1]["Close"]):
                    return False
            return True
        except Exception as err:
            raise Exception(str(err))

