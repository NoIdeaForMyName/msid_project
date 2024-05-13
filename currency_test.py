from forex_python.converter import CurrencyRates
import datetime as dt

def main():
    c = CurrencyRates()
    c.get_rate('USD', 'PLN')

if __name__ == "__main__":
    main()
