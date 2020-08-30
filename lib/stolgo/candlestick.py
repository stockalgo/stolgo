from stolgo.exception import BadDataError

class CandleStick:

    def is_bearish_candle(self,candle):
        return candle["Close"] <  candle["Open"]

    def is_bullish_candle(self,candle):
        return candle["Close"] > candle["Open"]

    def is_bullish_engulfing(self,candles,pos=-1):
        if candles.shape[0] < 2:
                raise BadDataError("Minimun two candles require")
        curr_candle = candles.iloc[pos]
        prev_candle = candles.iloc[pos-1]

        #check for pattern
        if  (self.is_bearish_candle(prev_candle)\
            and curr_candle["Close"] > prev_candle["Open"] \
            and curr_candle["Open"] <prev_candle["Close"]):
            return True
        return False