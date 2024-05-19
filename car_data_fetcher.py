from typing import Any
import requests
import bs4
from bs4 import BeautifulSoup
import csv
import time
import os

from car_parsing import CarParser, OLX_CarParser, OTOMOTO_CarParser, parseStatus


def get_html_content(url: str, retries=3):
    """
    tries to connect to the given url and returns html content from the website
    """
    if retries < 0:
        return None
    headers = {  # without it, server may recognize this scraper as a bot and won't share resources
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check for any errors in the HTTP response
        if len(response.text) < 10000:
            print("Response length was too small")
            print(url)
            return get_html_content(url, retries - 1)
        return response
    except Exception as e:
        print(e)
        time.sleep(
            2
        )  # sometimes error is caused by the scraper running too fast - the server is blocking resources
        return get_html_content(url, retries - 1)


def get_car_href_list(url):
    """
    returns list of all urls with car offers
    """
    response = get_html_content(url, retries=50)
    if response is None:
        raise requests.exceptions.RequestException(
            "An error during fetching has occured"
        )
    soup = BeautifulSoup(response.text, "html.parser")

    car_container = soup.find("div", attrs={"data-testid": "search-results"})
    if not isinstance(car_container, bs4.Tag):
        print(
            "Site does not have demanded element: {data-testid: search-results}:", url
        )
        print("soup len:", len(soup.text))
        print("response len:", len(response.text))
        return []
    car_list = car_container.find_all("article", class_="ooa-yca59n e1i3khom0")
    car_href_list = [article.find("a")["href"] for article in car_list]

    return car_href_list


def get_cars_to_parse(car_urls: list[str]) -> tuple[list[CarParser], int]:
    """
    from list of urls with car offers, it creates and returns a list of CarParser objects
    that contain all informations about the cars from the website
    """
    failed = 0
    parsed_car_list: list[CarParser] = []
    url_counter = 0
    for url in car_urls:
        html = get_html_content(url)
        if html is None:  # unable to fetch data about this specific car
            failed += 1
            continue
        parsed_car_list.append(OTOMOTO_CarParser(html.text))
        url_counter += 1
    return parsed_car_list, failed


def parse_cars(cars_list: list[CarParser]) -> int:
    """
    parses every car provided in the input list

    modifies the input list so that only spccesfully parsed cars stay

    returns number of failed parsing attempt
    """
    for car in cars_list:
        car.parse_html()
    car_nb = len(cars_list)
    for i in reversed(range(len(cars_list))):
        if not cars_list[i].parsed == parseStatus.SUCCESFULLY_PARSED:
            del cars_list[i]
    failed = car_nb - len(cars_list)
    return failed


def write_to_csv(detail_dict_list: list[dict[str, str]], filename):
    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = detail_dict_list[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if csvfile.tell() == 0:
            writer.writeheader()
        for detail_dict in detail_dict_list:
            writer.writerow(detail_dict)


def get_all_pagination_urls(first_url: str) -> list[str]:
    """
    from the first page, given as an argument, returns links to the next pages with cars
    """
    infix = "?page="
    html = get_html_content(first_url)
    if html is None:
        raise requests.exceptions.RequestException(
            "An error during initial fetching has occured"
        )
    soup = BeautifulSoup(html.text, "html.parser")
    paginations = soup.find("ul", class_="pagination-list")
    if isinstance(paginations, bs4.NavigableString) or paginations is None:
        raise requests.exceptions.RequestException(
            "An error during initial fetching has occured"
        )
    last_url_number = int(
        paginations.find_all("li", attrs={"data-testid": "pagination-list-item"})[
            -1
        ].text
    )

    return [
        first_url + infix + str(counter) for counter in range(1, last_url_number + 1)
    ]


def main():

    car_type_pagination_url_dict = {
        ("Volkswagen", "Golf"): "https://www.otomoto.pl/osobowe/volkswagen/golf",
        ("BMW", "Seria 3"): "https://www.otomoto.pl/osobowe/bmw/seria-3",
        ("Opel", "Corsa"): "https://www.otomoto.pl/osobowe/opel/corsa",
    }

    # minimum pagination: - so that for every car type there will be approx. the same number of samples

    pages_per_car = min(
        [
            len(get_all_pagination_urls(url))
            for url in car_type_pagination_url_dict.values()
        ]
    )
    cars_per_page = len(
        get_car_href_list(list(car_type_pagination_url_dict.values())[0])
    )
    car_nb_per_model = pages_per_car * cars_per_page

    sum_failed = 0
    for (brand, model), first_url in car_type_pagination_url_dict.items():
        print(f"Fetching data for {brand} {model}")
        csv_filename = f"{brand}_{model}.csv"
        urls = get_all_pagination_urls(first_url)[:pages_per_car]

        car_pages_nb = 0
        pagination_sites_car_urls: list[list[str]] = []
        for url in urls:
            print("Done:", round(car_pages_nb * 100 / car_nb_per_model, 2), "%")
            car_list = get_car_href_list(url)
            car_pages_nb += len(car_list)
            if car_list != []:
                pagination_sites_car_urls.append(car_list)
            if car_pages_nb >= car_nb_per_model:
                diff = car_pages_nb - car_nb_per_model
                lst_len = len(pagination_sites_car_urls[-1])
                del pagination_sites_car_urls[-1][lst_len - diff :]
                break
        print()
        [print("car list:", len(car)) for car in pagination_sites_car_urls]

        if os.path.exists(csv_filename):
            print("Overwriting", csv_filename)
            os.remove(csv_filename)
        loop_size = len(pagination_sites_car_urls)
        counter = 0
        for car_urls in pagination_sites_car_urls:
            print("Left:", round(counter * 100 / loop_size, 2), "%")
            counter += 1
            cars, failed = get_cars_to_parse(car_urls)
            sum_failed += failed
            sum_failed += parse_cars(cars)
            write_to_csv([car.details for car in cars], csv_filename)
    print(f"Overall failed: {sum_failed}")


if __name__ == "__main__":
    main()
