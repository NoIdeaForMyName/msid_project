import abc
import bs4
from bs4 import BeautifulSoup
from enum import Enum, auto
import re

from matplotlib.pylab import det

class parseStatus(Enum):
    UNPARSED = auto()
    SUCCESFULLY_PARSED = auto()
    UNSUCCESFULLY_PARSED = auto()


class CarParser(metaclass=abc.ABCMeta):
    def __init__(self, html) -> None:
        #self.html: str = html
        self.soup = BeautifulSoup(html, 'html.parser')
        self.parsed: parseStatus = parseStatus.UNPARSED

        self.details = {
            'brand': 'Unknown',
            'model': 'Unknown',
            'generation': 'Unknown',
            'eng_cap': 'Unknown', # in cm^3
            'prod_year': 'Unknown',
            'power': 'Unknown', # KM
            'fuel_type': 'Unknown', # gasoline | diesel | lpg
            'car_body': 'Unknown', # combi | hatchback | convertible etc.
            'mileage': 'Unknown', # km
            'color': 'Unknown',
            'condition': 'Unknown', # damaged | undamaged
            'transmission': 'Unknown', # manual | automatic
            'origin': 'Unknown', # poland | germany etc.
            'price': 'Unknown',
            'source': 'Unknown'
        }
    
    @abc.abstractmethod
    def parse_html(self) -> parseStatus:
        pass

    @abc.abstractmethod
    def get_price(self) -> str:
        pass


class OLX_CarParser(CarParser):
    '''
    OLX parser does not support 'brand' detail, so it can be passed in constructor
    '''

    translation = {
        'Model': 'model',
        'Poj. silnika': 'eng_cap',
        'Rok produkcji': 'prod_year',
        'Moc silnika': 'power',
        'Paliwo': 'fuel_type',
        'Typ nadwozia': 'car_body',
        'Przebieg': 'mileage',
        'Kolor': 'color',
        'Stan techniczny': 'condition',
        'Skrzynia biegów': 'transmission',
        'Kraj pochodzenia': 'origin',
    }

    def __init__(self, html, brand:str='Unknown') -> None:
        super().__init__(html)
        self.details['brand'] = brand
        self.details['source'] = 'OLX'

    def parse_html(self) -> parseStatus:
        car_data = self.soup.find('ul', class_='css-sfcl1s')
        if car_data is None or isinstance(car_data, bs4.NavigableString):
            self.parsed = parseStatus.UNSUCCESFULLY_PARSED
            return self.parsed
        details_list: list[str] = [t.text for t in car_data.find_all('li', class_='css-1r0si1e')][1:]
        self.fill_details(details_list)
        self.parsed = parseStatus.SUCCESFULLY_PARSED
        return self.parsed
    

    def fill_details(self, det):
        name_detail_list = [[d_.strip() for d_ in d.split(':')] for d in det]
        for name, detail in name_detail_list:
            key = OLX_CarParser.translation.get(name, None)
            if key:
                self.details[OLX_CarParser.translation[name]] = detail
        self.details['price'] = self.get_price()
        gen = self.get_generation()
        if gen is not None:
            self.details['generation'] = gen

    def get_price(self) -> str:
        price_tag = self.soup.find('div', attrs={'data-testid': 'ad-price-container'})
        if isinstance(price_tag, bs4.NavigableString) or price_tag is None:
            return ''
        return price_tag.text
    
    def get_generation(self) -> str | None:
        model = self.details['model']
        if model == 'Unknown':
            return None
        title_tag = self.soup.find('title')
        if not isinstance(title_tag, bs4.Tag):
            return None
        title_content = title_tag.text.split()
        for i in range(len(title_content)):
            if title_content[i] == model and i != len(title_content)-1:
                return title_content[i+1]
        return None


'''
<div data-testid="ad-price-container" class="css-e2ir3r"><h3 class="css-12vqlj3">9 999 zł</h3></div>
'''


class OTOMOTO_CarParser(CarParser):
    
    translation = {
        'Marka pojazdu': 'brand',
        'Model pojazdu': 'model',
        'Generacja': 'generation',
        'Pojemność skokowa': 'eng_cap',
        'Rok produkcji': 'prod_year',
        'Moc': 'power',
        'Rodzaj paliwa': 'fuel_type',
        'Typ nadwozia': 'car_body',
        'Przebieg': 'mileage',
        'Kolor': 'color',
        'Stan': 'condition',
        'Skrzynia biegów': 'transmission',
        'Kraj pochodzenia': 'origin',
    }

    def __init__(self, html) -> None:
        super().__init__(html)
        self.details['source'] = 'OTOMOTO'

    def parse_html(self) -> parseStatus:
        #car_data = soup.find('div', class_='ooa-1x860b3 e18eslyg2')
        car_data = self.soup.find('div', attrs={'data-testid': 'content-details-section'})
        if car_data is None or isinstance(car_data, bs4.NavigableString):
            self.parsed = parseStatus.UNSUCCESFULLY_PARSED
            return self.parsed
        car_data_list = self.soup.find_all('div', attrs={'data-testid': 'advert-details-item'})
        details_list: list[tuple[str, str]] = [tuple(t.text for t in tag.find_all(re.compile('[p,a]'))) for tag in car_data_list]
        details_list: list[tuple[str, str]] = [(tuple_[0], 'Unknown') if len(tuple_) != 2 else tuple_ for tuple_ in details_list]
        self.fill_details(details_list)
        self.parsed = parseStatus.SUCCESFULLY_PARSED
        return self.parsed
    

    def fill_details(self, det):
        for name, detail in det:
            name, detail = name.strip(), detail.strip()
            key = OTOMOTO_CarParser.translation.get(name, None)
            if key:
                self.details[OTOMOTO_CarParser.translation[name]] = detail
        self.details['price'] = self.get_price()

    def get_price(self) -> str:
        price_tag = self.soup.find('h3', class_='offer-price__number')
        if isinstance(price_tag, bs4.NavigableString) or price_tag is None or price_tag.parent is None:
            return ''
        return price_tag.parent.text
