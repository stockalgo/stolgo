import pytest

legacy_nse_data = pytest.importorskip(
    "stolgo.nse_data", reason="legacy NSE module is not part of the greenfield package"
)

NseData = legacy_nse_data.NseData

def main():
    nse_data = NseData()
    nse_data.get_option_chain_excel('BANKNIFTY','30APR2020')
    
if __name__ == "__main__":
    main()
    
