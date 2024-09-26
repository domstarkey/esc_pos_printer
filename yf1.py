import yfinance as yf
from pprint import pprint

msft = yf.Ticker("SAP")

# get all stock info
pprint(msft.info)