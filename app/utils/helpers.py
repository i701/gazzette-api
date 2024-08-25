"""Helper functions for the Gazette API."""

from datetime import datetime
import re
from app.utils.constants import MONTH_TRANSLATIONS
from typing import Optional, List
import httpx
import requests
from bs4 import BeautifulSoup as bs
from app.utils.constants import (
    GAZETTE_BASE_URL,
    IULAAN_SEARCH_URL,
)


def detect_component(part):
    """Detect if the part is a day, month, year, or time."""
    if re.match(r"^\d{1,2}$", part):
        return "day"
    elif re.match(r"^\d{4}$", part):
        return "year"
    elif re.match(r"^\d{2}:\d{2}$", part):
        return "time"
    elif part in MONTH_TRANSLATIONS:
        return "month"
    return "unknown"


def maldivian_to_iso(date_str):
    """Convert a maldivian date string to ISO 8601."""
    parts = date_str.split()

    day = None
    month = None
    year = None
    time_str = None

    for part in parts:
        component_type = detect_component(part)
        if component_type == "day":
            day = part
        elif component_type == "month":
            month = MONTH_TRANSLATIONS.get(part, "Unknown")
        elif component_type == "year":
            year = part
        elif component_type == "time":
            time_str = part

    if day is None or month is None or year is None:
        raise ValueError("Date string is missing required components")

    if time_str is None:
        time_str = "00:00"

    date_formatted = f"{month} {day}, {year} {time_str}"

    try:
        dt_obj = datetime.strptime(date_formatted, "%B %d, %Y %H:%M")
    except ValueError:
        dt_obj = datetime.strptime(date_formatted, "%B %d, %Y")

    iso_date = dt_obj.isoformat()

    return iso_date


async def iulaan_search(
    page: int = 1,
    iulaan_type: str = "",
    category: Optional[str] = "",
    q: Optional[str] = "",
    open_only: int = 0,
    start_date: Optional[str] = "",
    end_date: Optional[str] = "",
    office: Optional[str] = "",
) -> List[dict]:
    """Search for job and tender listings based on provided parameters."""
    return_data = []
    meta_data = {}
    print("IULAAN TYPE -> ", iulaan_type)
    print("JOB CATEGORY -> ", category)
    print("Q -> ", q)
    print("OPEN ONLY -> ", open_only)
    print("START DATE -> ", start_date)
    print("END DATE -> ", end_date)
    print("OFFICE -> ", office)
    url = (
        f"{GAZETTE_BASE_URL}{IULAAN_SEARCH_URL}?"
        f"type={iulaan_type}&job-category={category}"
        f"&office={office}&page={page}"
        f"&start-date={start_date}&end-date={end_date}"
        f"&open-only={open_only}"
        f"&q={q}"
    )
    print("GAZETTE URL -> ", url)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        print("HTTPX status code (iulaan_search)-> ", response.status_code)
    if response.status_code == 200:
        soup = bs(response.content, "html.parser")
        soup.prettify()
        items = soup.find_all("div", class_="items")
        total = soup.find("div", class_="iulaan-type-title")
        total_results = total.text.split(" ")[1].strip()
        total_pages = current_page = next_page_link = None
        meta_data["total_results"] = int(total_results)

        pagination = soup.find("ul", class_="pagination")
        if pagination:
            total_pages_items = pagination.find_all("li")
            if len(total_pages_items) > 1:
                total_pages = total_pages_items[-2].text.strip()
                meta_data["total_pages"] = int(total_pages)
            else:
                total_pages = "1"
                meta_data["total_pages"] = int(total_pages)

            current_page_item = pagination.find("li", class_="active")
            if current_page_item:
                current_page = current_page_item.text.strip()
                meta_data["current_page"] = int(current_page)
            else:
                current_page = "1"
                meta_data["current_page"] = int(current_page)

            if len(total_pages_items) > 1:
                last_item = total_pages_items[-1].find("a")
                if last_item is not None and "href" in last_item.attrs:
                    next_page_link = last_item["href"]
                else:
                    next_page_link = None
            else:
                next_page_link = None

            meta_data["next_page_link"] = next_page_link

        for item in items:
            item_body = {}

            title = item.find("a", class_="iulaan-title")
            item_body["url"] = title.get("href")
            item_body["id"] = [
                int(segment)
                for segment in item_body["url"].split("/")
                if segment.isdigit()
            ][0]
            item_body["title"] = title.text

            vendor = item.find("a", class_="iulaan-office")
            iulaan_type = item.find("a", class_="iulaan-type")

            item_body["vendor"] = vendor.text.strip()
            item_body["vendor_url"] = vendor.get("href").strip()
            item_body["iulaan_type"] = iulaan_type.text.strip()
            info = item.find_all("div", class_="info")

            for i in info:
                my_list = i.text.strip().split()[1:]

                if len(my_list) == 3:
                    date = " ".join(my_list)
                    item_body["date"] = maldivian_to_iso(date)
                if len(my_list) == 4:
                    deadline = " ".join(my_list)
                    item_body["deadline"] = maldivian_to_iso(deadline)

            return_data.append(item_body)

    return_data = {"meta_data": meta_data, "results": return_data}
    return (return_data, url)


async def iulaan_search_with_url(
    url: Optional[str] = "",
) -> List[dict]:
    """Search for listings from url."""
    return_data = []
    meta_data = {}
    response = requests.get(url, timeout=10)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        print("httpx status code (iulaan_search_with_url) -> ", response.status_code)
        if response.status_code == 301:
            print("trying with requests...")
            response = requests.get(url, timeout=10)

    if response.status_code == 200:
        soup = bs(response.content, "html.parser")
        soup.prettify()
        items = soup.find_all("div", class_="items")
        total = soup.find("div", class_="iulaan-type-title")
        total_results = total.text.split(" ")[1].strip()
        total_pages = current_page = next_page_link = None
        meta_data["total_results"] = int(total_results)

        pagination = soup.find("ul", class_="pagination")
        if pagination:
            total_pages_items = pagination.find_all("li")
            if len(total_pages_items) > 1:
                total_pages = total_pages_items[-2].text.strip()
                meta_data["total_pages"] = int(total_pages)
            else:
                total_pages = "1"
                meta_data["total_pages"] = int(total_pages)

            current_page_item = pagination.find("li", class_="active")
            if current_page_item:
                current_page = current_page_item.text.strip()
                meta_data["current_page"] = int(current_page)
            else:
                current_page = "1"
                meta_data["current_page"] = int(current_page)

            if len(total_pages_items) > 1:
                next_page_link = total_pages_items[-1].find("a")["href"]
                meta_data["next_page_link"] = next_page_link
            else:
                next_page_link = None

        for item in items:
            item_body = {}

            title = item.find("a", class_="iulaan-title")
            item_body["url"] = title.get("href")
            item_body["id"] = [
                int(segment)
                for segment in item_body["url"].split("/")
                if segment.isdigit()
            ][0]
            item_body["title"] = title.text

            vendor = item.find("a", class_="iulaan-office")
            iulaan_type = item.find("a", class_="iulaan-type")

            item_body["vendor"] = vendor.text.strip()
            item_body["vendor_url"] = vendor.get("href").strip()
            item_body["iulaan_type"] = iulaan_type.text.strip()
            info = item.find_all("div", class_="info")

            for i in info:
                my_list = i.text.strip().split()[1:]

                if len(my_list) == 3:
                    date = " ".join(my_list)
                    item_body["date"] = maldivian_to_iso(date)
                if len(my_list) == 4:
                    deadline = " ".join(my_list)
                    item_body["deadline"] = maldivian_to_iso(deadline)

            return_data.append(item_body)

    return_data = {"meta_data": meta_data, "results": return_data}
    return return_data
