import requests
import bs4
from bs4 import BeautifulSoup
import csv

from car_parsing import OLX_CarParser, OTOMOTO_CarParser


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
        return get_html_content(url, retries-1)


def get_car_href_list(url):
    url = 'https://www.olx.pl/motoryzacja/samochody/volkswagen/?search%5Bfilter_enum_model%5D%5B0%5D=golf'
    url_prefix = 'https://www.olx.pl'

    response = get_html_content(url)
    if response is None:
        raise requests.exceptions.RequestException('An error during fetching has occured')

    soup = BeautifulSoup(response.text, 'html.parser')
    cars = soup.find('div', class_='css-oukcj3')
    if cars is None or isinstance(cars, bs4.NavigableString):
        return []
    #car_list = cars.find_all('div', class_='css-1sw7q4x')

    car_href_list = [t.get('href') for t in cars.find_all('a', class_='css-z3gu2d')]
    car_href_list = list(map(lambda href: url_prefix+href if href[:2] == '/d' else href, car_href_list))
    
    olx_car_href_list = list(filter(lambda href: href.find('olx') != -1, car_href_list))
    otomoto_car_href_list = list(filter(lambda href: href.find('otomoto') != -1, car_href_list))

    print('olx:', len(olx_car_href_list))
    print('otomoto', len(otomoto_car_href_list))

    parsed_car_list = []
    for url_olx, url_oto in zip(olx_car_href_list, otomoto_car_href_list): #[:5]
        #print("URL OLX:", url_olx)
        #print("URL OTOMOTO:", url_oto)
        print('.', end='', flush=True)
        html_olx = get_html_content(url_olx)
        html_oto = get_html_content(url_oto)
        if html_olx:
            parsed_car_list.append(OLX_CarParser(html_olx.text))
        if html_oto:
            parsed_car_list.append(OTOMOTO_CarParser(html_oto.text))

    for car in parsed_car_list: car.parse_html()
    #[print(l.details) for l in parsed_car_list]

    with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = parsed_car_list[0].details.keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for car in parsed_car_list:
            writer.writerow(car.details)


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
    first_url = 'https://www.olx.pl/motoryzacja/samochody/volkswagen/?search%5Bfilter_enum_model%5D%5B0%5D=golf'
    urls = get_all_pagination_urls(first_url)
    [print(x) for x in urls]
    #get_car_href_list(first_url)

if __name__ == "__main__":
    main()
