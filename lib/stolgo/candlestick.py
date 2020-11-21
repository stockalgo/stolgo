from stolgo.exception import BadDataError

class CandleStick:

    def is_bearish_candle(self,candle):
        if candle["Close"] <  candle["Open"]:
            return True
        return False

    def is_bullish_candle(self,candle):
        if candle["Close"] > candle["Open"]:
            return True
        return False

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
    
    def is_hammer_candle(self,candle,pos=-1,lower_wick = 0.6, body = 0.2, upper_wick = 0.2):
        curr_candle = candle.iloc[pos]
        if candles.shape[0] < 1:
                raise BadDataError("Minimun one candles require")
        candle_length = curr_candle["High"] - curr_candle["Low"]
        if self.is_bullish_candle(curr_candle):
            candle_upper_wick = curr_candle["High"]-curr_candle["Close"]
            candle_lower_wick = curr_candle["Open"]-curr_candle["Low"]
            candle_body = curr_candle["Close"] - curr_candle["Open"]
            if candle_body <= body * candle_length and candle_upper_wick <= upper_wick * candle_length:
                return True
        elif self.is_bearish_candle(curr_candle):
            candle_upper_wick = curr_candle["High"]-curr_candle["Open"]
            candle_lower_wick = curr_candle["Close"]-curr_candle["Low"]
            candle_body = curr_candle["Open"] - curr_candle["Close"]
            if candle_body <= body * candle_length and candle_upper_wick <= upper_wick * candle_length:
                return True
        return False
    
    def is_inverse_hammer_candle(self,candle,pos=-1,lower_wick = 0.2, body = 0.2, upper_wick = 0.6):
        curr_candle = candle.iloc[pos]
        candle_length = curr_candle["High"] - curr_candle["Low"]
        if self.is_bullish_candle(curr_candle):
            candle_body = curr_candle["Close"] - curr_candle["Open"]
            candle_upper_wick = curr_candle["High"]-curr_candle["Close"]
            candle_lower_wick = curr_candle["Open"]-curr_candle["Low"]
            if candle_body <= body * candle_length and candle_lower_wick <= lower_wick * candle_length:
                return True
        elif self.is_bearish_candle(curr_candle):
            candle_body = curr_candle["Open"] - curr_candle["Close"]
            candle_upper_wick = curr_candle["Open"]-curr_candle["High"]
            candle_lower_wick = curr_candle["Close"]-curr_candle["Low"]
            if candle_body <= body * candle_length and candle_lower_wick <= lower_wick * candle_length:
                return True
        return False
    
    def is_doji_candle(self,candle,pos=-1,lower_wick = 0.4, body = 0.02, upper_wick = 0.4):
        curr_candle = candle.iloc[pos]
        candle_length = curr_candle["High"] - curr_candle["Low"]
        if self.is_bullish_candle(curr_candle):
            candle_body = curr_candle["Close"] - curr_candle["Open"]
            candle_upper_wick = curr_candle["High"]-curr_candle["Close"]
            candle_lower_wick = curr_candle["Open"]-curr_candle["Low"]
            if candle_body <= body * candle_length and candle_upper_wick >= upper_wick*candle_length and candle_lower_wick >= lower_wick*candle_length:
                return True
        elif self.is_bearish_candle(curr_candle):
            candle_body = curr_candle["Open"] - curr_candle["Close"]
            candle_upper_wick = curr_candle["High"]-curr_candle["Open"]
            candle_lower_wick = curr_candle["Close"]-curr_candle["Low"]
            if candle_body <= body * candle_length and candle_upper_wick >= upper_wick*candle_length and candle_lower_wick >= lower_wick*candle_length:
                return True
        return False