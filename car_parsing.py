import abc
import bs4
from bs4 import BeautifulSoup
from enum import Enum, auto

class parseStatus(Enum):
    UNPARSED = auto()
    SUCCESFULLY_PARSED = auto()
    UNSUCCESFULLY_PARSED = auto()


class CarParser(metaclass=abc.ABCMeta):
    def __init__(self, html) -> None:
        self.html: str = html
        self.parsed: parseStatus = parseStatus.UNPARSED

        self.details = {
            #'brand': '',
            'model': '',
            'eng_cap': -1, # in cm^3
            'prod_year': -1,
            'power': -1, # KM
            'fuel_type': '', # gasoline | diesel | lpg
            'car_body': '', # combi | hatchback | convertible etc.
            'mileage': -1, # km
            'color': '',
            'condition': '', # damaged | undamaged
            'transmission': '', # manual | automatic
            'origin': '', # poland | germany etc.
        }
    
    @abc.abstractmethod
    def parse_html(self) -> parseStatus:
        pass


class OLX_CarParser(CarParser):

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

    def __init__(self, html) -> None:
        super().__init__(html)

    def parse_html(self) -> parseStatus:
        soup = BeautifulSoup(self.html, 'html.parser')
        car_data = soup.find('ul', class_='css-sfcl1s')
        if car_data is None or isinstance(car_data, bs4.NavigableString):
            self.parsed = parseStatus.UNSUCCESFULLY_PARSED
            return self.parsed
        details_list: list[str] = [t.text for t in car_data.find_all('li', class_='css-1r0si1e')][1:]
        self.fill_details(details_list)
        self.parsed = parseStatus.SUCCESFULLY_PARSED
        return self.parsed
    

    def fill_details(self, det):
        name_detail_list = [d.split(':') for d in det]
        for name, detail in name_detail_list:
            key = OLX_CarParser.translation.get(name, None)
            if key:
                self.details[OLX_CarParser.translation[name]] = detail


class OTOMOTO_CarParser(CarParser):
    
    translation = {
        #'Marka pojazdu': 'brand',
        'Model pojazdu': 'model',
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

    def parse_html(self) -> parseStatus:
        soup = BeautifulSoup(self.html, 'html.parser')
        #car_data = soup.find('div', class_='ooa-1x860b3 e18eslyg2')
        car_data = soup.find('div', attrs={'data-testid': 'content-details-section'})
        if car_data is None or isinstance(car_data, bs4.NavigableString):
            self.parsed = parseStatus.UNSUCCESFULLY_PARSED
            return self.parsed
        car_data_list = soup.find_all('div', attrs={'data-testid': 'advert-details-item'})
        details_list: list[tuple[str, str]] = [(t.find_all()[0].text, t.find_all()[1].text) for t in car_data_list]
        #details_list: list[str] = [t.text for t in car_data]
        self.fill_details(details_list)
        self.parsed = parseStatus.SUCCESFULLY_PARSED
        return self.parsed
    

    def fill_details(self, det):
        for name, detail in det:
            key = OTOMOTO_CarParser.translation.get(name, None)
            if key:
                self.details[OTOMOTO_CarParser.translation[name]] = detail
