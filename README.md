# stolgo

stolgo is a Python library for dealing with financial data such as stocks, derivatives, commodities, and cryptocurrencies.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install foobar.

```bash
pip install stolgo
```

## Usage

```python
from stolgo.nse_data import NseData()

nd = NseData() # returns 'NseData object'. can be use to get nse data.

nd.get_option_chain_excel(symbol,expiry_data,filepath) #dumps option chain to file_path
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
