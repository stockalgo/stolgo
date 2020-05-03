from stolgo.nse_data import NseData

def main():
    nse_data = NseData()
    nse_data.get_option_chain_excel('BANKNIFTY','30APR2020')
    
if __name__ == "__main__":
    main()
    
