
<p align="center"><a href="http://stolgo.com" target="_blank"><img src="https://raw.githubusercontent.com/stockalgo/stolgo/master/stolgo.svg"></a> </p>

stolgo is a Python library for dealing with financial data such as stocks, derivatives, commodities, and cryptocurrencies.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install stolgo.

```bash
pip install stolgo
```
  
# For data feed, Stolgo uses [bandl.io](https://bandl.io), Where by just calling get_date API, You can get data from your favourite broker or directly from exchange website or yahoo finance.

## Usage

### Get the data, for example using yahoo finance module form [bandl](https://bandl.io)
```python
from bandl.yfinance import Yfinance
testObj = Yfinance() # returns 'Yfinance class object'.
#to get indian stock data
dfs = testObj.get_data("SBIN",start="21-Jan-2020") #retruns data from 21Jan 2020 to till today
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Kindly follow PEP 8 Coding Style guidelines. Refer: https://www.python.org/dev/peps/pep-0008/

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
