# stolgo

stolgo is a Python library for dealing with financial data such as stocks, derivatives, commodities, and cryptocurrencies.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install stolgo.

```bash
pip install stolgo
```

## Usage

### To import NSE Data Module
```python
from stolgo.nse_data import NseData()
nd = NseData() # returns 'NseData object'. can be use to get nse data.
```
#### To get Option chain data
```python
expiry_dates = nd.get_oc_exp_dates(symbol) #return available expiry dates
nd.get_option_chain_excel(symbol,expiry_date,filepath) #dumps option chain to file_path
# or get in pandas dateframe
bn_df = nd.get_option_chain_df(symbol, expiry_date,dayfirst=False) #returns option chain in pandas data frame.
```
#### To get stock historical data.
```python
data_frame = nd.get_data(symbol,series="EQ",start=None,end=None,periods=None,dayfirst=False) #returns historical data in pandas data frames
```

#### To get FII/DII data.
```python
part_oi_df = nd.get_part_oi_df(start=None,end=None,periods=None,dayfirst=False,workers=None)
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Kindly follow PEP 8 Coding Style guidelines. Refer: https://www.python.org/dev/peps/pep-0008/

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)