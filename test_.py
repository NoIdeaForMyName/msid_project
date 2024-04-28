import requests
import bs4
from bs4 import BeautifulSoup
import csv
import time

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
    # cars = soup.find('div', class_='css-oukcj3')
    # if cars is None or isinstance(cars, bs4.NavigableString):
    #     return []

    #car_href_list = [t.find('a')['href'] for t in cars.find_all('div', attrs={'data-cy':'l-card'})]
    car_href_list = [t.find('a')['href'] for t in soup.find_all('div', attrs={'data-cy':'l-card'})]
    car_href_list = list(map(lambda href: url_prefix+href if href[:2] == '/d' else href, car_href_list))
    
    # olx_car_href_list = list(filter(lambda href: href.find('olx') != -1, car_href_list))
    # otomoto_car_href_list = list(filter(lambda href: href.find('otomoto') != -1, car_href_list))

    # print('olx:', len(olx_car_href_list))
    # print('otomoto', len(otomoto_car_href_list))

    # print("ALL")
    # [print(x) for x in car_href_list]
    # print("OLX")
    # [print(x) for x in olx_car_href_list]

    # print("OTOMOTO")
    # [print(x) for x in otomoto_car_href_list]


    # FOR TESTING (DELETE LATER) ###################################
    # car_href_list = [otomoto_car_href_list[0]]
    # print("TEST:", car_href_list[0], car_href_list[0].find('olx'))
    # import random
    # car_href_list = [random.choice(car_href_list)]
    # print('sajisoa', car_href_list[0])
    # car_href_list = random.choices(otomoto_car_href_list, k=5)
    # FOR TESTING (DELETE LATER) ###################################

    parsed_car_list: list[CarParser] = []
    url_number = len(car_href_list)
    url_counter = 0
    print(f'Fetching data from: {url}')
    print(f'Number of cars: {url_number}')
    for url in car_href_list:
        html = get_html_content(url)
        if html is None: # unable to fetch data about this specific car
            continue
        if url.find('olx') != -1:
            parsed_car_list.append(OLX_CarParser(html.text))
        elif url.find('otomoto') != -1:
            parsed_car_list.append(OTOMOTO_CarParser(html.text))
        url_counter += 1
        print(f'{round(url_counter*100/url_number, 2)}%', end='; ', flush=True)
    print()

    # for url_olx, url_oto in zip(olx_car_href_list, otomoto_car_href_list): #[:5]
    #     #print("URL OLX:", url_olx)
    #     #print("URL OTOMOTO:", url_oto)
    #     print('.', end='', flush=True)
    #     html_olx = get_html_content(url_olx)
    #     html_oto = get_html_content(url_oto)
    #     if html_olx:
    #         parsed_car_list.append(OLX_CarParser(html_olx.text))
    #     if html_oto:
    #         parsed_car_list.append(OTOMOTO_CarParser(html_oto.text))

    for car in parsed_car_list: car.parse_html()
    car_nb = len(parsed_car_list)
    parsed_car_list = list(filter(lambda car: car.parsed == parseStatus.SUCCESFULLY_PARSED, parsed_car_list))
    failed = car_nb - len(parsed_car_list)

    with open('output.csv', 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = parsed_car_list[0].details.keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for car in parsed_car_list:
            writer.writerow(car.details)

    return failed


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
    # print('\n\n\nTESTING ONCE AGAIN FOR ONE URL...')
    # get_car_href_list(first_url)

    with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
        pass
    failed_sum = 0
    for url in urls:
        failed_sum += get_car_href_list(url)

    with open('failed.log', 'w') as file:
        file.write(str(failed_sum))
        
    import os
    os.system('shutdown -s -t 10')

if __name__ == "__main__":
    main()
