from typing import Any
import requests
import bs4
from bs4 import BeautifulSoup
import csv
import time
import os

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
    url_prefix = 'https://www.olx.pl'
    response = get_html_content(url, retries=50)
    if response is None:
        raise requests.exceptions.RequestException('An error during fetching has occured')
    soup = BeautifulSoup(response.text, 'html.parser')

    car_href_list = [t.find('a')['href'] for t in soup.find_all('div', attrs={'data-cy':'l-card'})]
    car_href_list = list(map(lambda href: url_prefix+href if href[:2] == '/d' else href, car_href_list))
    
    return car_href_list


def get_cars_to_parse(car_urls: list[str], olx_brand='Unknown') -> list[CarParser]:
    parsed_car_list: list[CarParser] = []
    url_number = len(car_urls)
    url_counter = 0
    for url in car_urls:
        html = get_html_content(url)
        if html is None: # unable to fetch data about this specific car
            continue
        if url.find('olx') != -1:
            parsed_car_list.append(OLX_CarParser(html.text, olx_brand))
        elif url.find('otomoto') != -1:
            parsed_car_list.append(OTOMOTO_CarParser(html.text))
        url_counter += 1
        print(f'{round(url_counter*100/url_number, 2)}%', end='; ', flush=True)
    print()
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
    html = get_html_content(first_url)
    if html is None:
        raise requests.exceptions.RequestException('An error during initial fetching has occured')
    soup = BeautifulSoup(html.text, 'html.parser')
    paginations = soup.find('ul', class_='pagination-list')
    if isinstance(paginations, bs4.NavigableString) or paginations is None:
        raise requests.exceptions.RequestException('An error during initial fetching has occured')
    last_url_number = int(paginations.find_all('li', class_='pagination-item')[-1].text)
    inline_placement_idx = first_url.find('search%')
    return [first_url[:inline_placement_idx] + 'page=' + str(counter)+'&' + first_url[inline_placement_idx:] for counter in range(1, last_url_number+1)]


def main():
    #first_url = 'https://www.olx.pl/motoryzacja/samochody/volkswagen/?search%5Bfilter_enum_model%5D%5B0%5D=golf'
    first_url = 'https://www.olx.pl/motoryzacja/samochody/volkswagen/q-golf-4/?search%5Bfilter_enum_model%5D%5B0%5D=golf'
    urls = get_all_pagination_urls(first_url)
    [print(x) for x in urls]

    csv_filename = 'output.csv'

    if os.path.exists("output.csv"):
        print('Overwriting', csv_filename)
        os.remove(csv_filename)

    print("TEST DLA 1 STRONY:")

    print(f'Fetching data from: {urls[0]}')
    import random
    car_urls = random.choices(get_car_href_list(urls[0]), k=7)
    print(f'Number of cars: {len(car_urls)}')
    cars = get_cars_to_parse(car_urls, 'Volkswagen')
    failed_nb = parse_cars(cars)
    print('Failed:', failed_nb)
    write_to_csv([car.details for car in cars], csv_filename)


if __name__ == "__main__":
    main()
