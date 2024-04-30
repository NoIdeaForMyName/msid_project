from typing import Any
import requests
import bs4
from bs4 import BeautifulSoup
import csv
import time
import os

from tqdm import tqdm

from car_parsing import CarParser, OLX_CarParser, OTOMOTO_CarParser, parseStatus


def get_html_content(url: str, retries=3):
    if retries < 0:
        return None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check for any errors in the HTTP response
        return response     
    except requests.exceptions.RequestException as e:
        time.sleep(2)
        return get_html_content(url, retries-1)


def get_car_href_list(url):
    response = get_html_content(url, retries=50)
    if response is None:
        raise requests.exceptions.RequestException('An error during fetching has occured')
    soup = BeautifulSoup(response.text, 'html.parser')

    car_container = soup.find('div', attrs={'data-testid': 'search-results'})
    if not isinstance(car_container, bs4.Tag):
        raise requests.exceptions.RequestException('Site does not have demanded element: {data-testid: search-results}')
    car_list = car_container.find_all('article', class_='ooa-yca59n e1i3khom0') 
    car_href_list = [article.find('a')['href'] for article in car_list]

    #car_href_list = [a['href'] for a in soup.find_all('a')]
    #car_href_list = [a.text for a in soup.find_all('a')]
    
    return car_href_list


def get_cars_to_parse(car_urls: list[str]) -> list[CarParser]:
    get_cars_to_parse.failed = 0
    parsed_car_list: list[CarParser] = []
    url_counter = 0
    for url in car_urls:
        html = get_html_content(url)
        if html is None: # unable to fetch data about this specific car
            get_cars_to_parse.failed += 1
            continue
        parsed_car_list.append(OTOMOTO_CarParser(html.text))
        url_counter += 1
        #print(f'{round(url_counter*100/url_number, 2)}%', end='; ', flush=True)
    #print()
    return parsed_car_list


#def parse_cars(cars_list: list[CarParser]) -> dict[parseStatus, list[CarParser]]:
def parse_cars(cars_list: list[CarParser]) -> int:
    for car in cars_list: car.parse_html()
    #return {key: list(filter(lambda car: car.parsed == key, cars_list)) for key in parseStatus.__members__.values()}

    car_nb = len(cars_list)
    cars_list = list(filter(lambda car: car.parsed == parseStatus.SUCCESFULLY_PARSED, cars_list))
    failed = car_nb - len(cars_list)
    return failed


def write_to_csv(detail_dict_list: list[dict[str, str]], filename):
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = detail_dict_list[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if csvfile.tell() == 0:
            writer.writeheader()
        for detail_dict in detail_dict_list:
            writer.writerow(detail_dict)


def get_all_pagination_urls(first_url: str) -> list[str]:
    infix = '?page='
    html = get_html_content(first_url)
    if html is None:
        raise requests.exceptions.RequestException('An error during initial fetching has occured')
    soup = BeautifulSoup(html.text, 'html.parser')
    paginations = soup.find('ul', class_='pagination-list')
    if isinstance(paginations, bs4.NavigableString) or paginations is None:
        raise requests.exceptions.RequestException('An error during initial fetching has occured')
    last_url_number = int(paginations.find_all('li', attrs={'data-testid':'pagination-list-item'})[-1].text)

    return [first_url + infix + str(counter) for counter in range(1, last_url_number+1)]


def main():
    #first_url = 'https://www.olx.pl/motoryzacja/samochody/volkswagen/?search%5Bfilter_enum_model%5D%5B0%5D=golf'
    #first_url = 'https://www.olx.pl/motoryzacja/samochody/volkswagen/q-golf-4/?search%5Bfilter_enum_model%5D%5B0%5D=golf'

    car_type_pagination_url_dict = {
        ('Volkswagen', 'Golf'): 'https://www.otomoto.pl/osobowe/volkswagen/golf',
        ('BMW', 'Seria 3'): 'https://www.otomoto.pl/osobowe/bmw/seria-3',
        ('Opel', 'Corsa'): 'https://www.otomoto.pl/osobowe/opel/corsa'
    }

    # minimum pagination:
    pages_per_car = min([len(get_all_pagination_urls(url)) for url in car_type_pagination_url_dict.values()])

    sum_failed = 0
    for (brand, model), first_url in car_type_pagination_url_dict.items():
        print(f'Fetching data for {brand} {model}')
        csv_filename = f'{brand}_{model}.csv'
        urls = get_all_pagination_urls(first_url)[:pages_per_car]
        if os.path.exists(csv_filename):
            print('Overwriting', csv_filename)
            os.remove(csv_filename)
        for url in tqdm(urls, desc='Every website'):
            car_urls = get_car_href_list(url)
            cars = get_cars_to_parse(car_urls)
            sum_failed += get_cars_to_parse.failed
            sum_failed += parse_cars(cars)
            write_to_csv([car.details for car in cars], csv_filename)
    print(f'Overall failed: {sum_failed}')

if __name__ == "__main__":
    main()
