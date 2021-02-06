
<p align="center"><a href="http://stolgo.com" target="_blank"><img src="https://raw.githubusercontent.com/stockalgo/stolgo/master/stolgo.svg"></a> </p>

Stolgo is Price Action Trading Analysis Library. Whenever the price reaches resistance during an upward trend, more sellers will enter the market and enter their sell trades. This is a simple price action rule. But How to automate this rule? How to write backtest for this? Stolgo provides APIs for Price Action Trading.

## Why Stolgo?
There are many libraries to backtest technical indicators (such as moving average crossover, MACD, RSI, etc.) base strategies, But What about the Price Action Trading?
A Price Action Trader uses support/resistance, candlestick pattern, trend, breakout, and other parameters based on price. You can use Stolgo to backtest your price action trading rules.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install stolgo.

```bash
pip install stolgo
```
  
# For data feed, Stolgo uses [bandl.io](https://bandl.io), Where by just calling get_date API, You can get data from your favourite broker or directly from exchange website or yahoo finance.

## Usage

### Get the data, for example using yahoo finance module form [bandl](https://bandl.io)
```bash
pip install bandl
```

### Example: Get Indian (NSE/BSE) stock data using Yahoo finance
```python
from bandl.yfinance import Yfinance
testObj = Yfinance() # returns 'Yfinance class object'.
dfs = testObj.get_data("SBIN",start="21-Jan-2020") #retruns data from 21Jan 2020 to till today
```

### Example: Get the data of Apple (US Stock) from Nasdaq
```python
from bandl.nasdaq import Nasdaq
testObj = Nasdaq() # returns 'Nasdaq class object'.
dfs = testObj.get_data("AAPL",periods=90) # returns last 90 days data
```

### check for bullish engulfing pattern
```python
from stolgo.candlestick import CandleStick
candle_test = CandleStick()
is_be = candle_test.is_bullish_engulfing(dfs)
```
### check for an inverted hammer candle pattern
```python
from stolgo.candlestick import CandleStick
candle_test = CandleStick()
is_it = candle_test.is_inverse_hammer_candle(dfs)
```

### check for breakout
```python
from stolgo.breakout import Breakout
breakout_test = Breakout()
is_be = breakout_test.is_breaking_out(dfs,periods=None,percentage=None) #periods:Number of candles,percentage: range of consolidation in percentage
```

## Todo
- Add unittest
- Add more features such as Support Resistance, momemtum, etc.
- Add Event-Driven Backtester

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Kindly follow PEP 8 Coding Style guidelines. Refer: https://www.python.org/dev/peps/pep-0008/

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
