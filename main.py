"""Main module for the Gazette API, providing job and tender search functionality."""

from typing import Optional, List
from fastapi import FastAPI, Query
import requests
from bs4 import BeautifulSoup as bs
from constants import GAZETTE_BASE_URL, IULAAN_SEARCH_URL, JOB_CATEGORIES, IULAAN_TYPES
from helpers import maldivian_to_iso

app = FastAPI()

# Constants from config.py


def iulaan_search(
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
    print(url)

    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        soup = bs(response.content, "html.parser")
        soup.prettify()
        items = soup.find_all("div", class_="items")
        total = soup.find("div", class_="iulaan-type-title")
        total_results = total.text.split(" ")[1].strip()
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

            # item_body["total_results"] = total_results.text.split(" ")[1].strip()
            item_body["vendor"] = vendor.text.strip()
            item_body["vendor_url"] = vendor.get("href").strip()
            item_body["iulaan_type"] = iulaan_type.text.strip()
            info = item.find_all("div", class_="info")
            # item_body["info"] = [i.text.strip().split(":")[1].strip() for i in info]
            # item_body["info"] = [i.text.strip() for i in info]
            for i in info:
                my_list = i.text.strip().split()[1:]
                # print("Length", len(my_list))

                if len(my_list) == 3:
                    date = " ".join(my_list)
                    item_body["date"] = maldivian_to_iso(date)
                    # print("date-> ", date)
                if len(my_list) == 4:
                    deadline = " ".join(my_list)
                    item_body["deadline"] = maldivian_to_iso(deadline)
                    # print("deadline-> ", deadline)
                # print("\n")
                # result = " ".join(my_list[1:])
                # item_body["info"] = result

            return_data.append(item_body)

    return (return_data, total_results)


@app.get("/search")
async def search(
    page: int = Query(1, ge=1),
    iulaan_type: Optional[str] = Query("", enum=list(IULAAN_TYPES.values())),
    category: Optional[str] = Query("", enum=list(JOB_CATEGORIES.values())),
    open_only: Optional[int] = Query(0, ge=0, le=1),
    start_date: Optional[str] = Query(""),
    end_date: Optional[str] = Query(""),
    q: Optional[str] = Query(""),
    office: Optional[str] = Query(""),
):
    """Search for iulaan listings based on provided parameters."""
    [results, total_results] = iulaan_search(
        category=category,
        iulaan_type=iulaan_type,
        open_only=open_only,
        start_date=start_date,
        end_date=end_date,
        office=office,
        q=q,
        page=page,
    )
    return {"page": page, "total_results": total_results, "results": results}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
