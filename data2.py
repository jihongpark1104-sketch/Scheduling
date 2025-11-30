import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from openpyxl.workbook import Workbook

import pandas as pd
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://classes.berkeley.edu"

TIME_RE = re.compile(
    r"(\d{1,2}:\d{2}\s*(am|pm))\s*-\s*(\d{1,2}:\d{2}\s*(am|pm))",
    re.IGNORECASE,
)


def fetch_html(url: str) -> bytes:
    print(f"[INFO] 요청 URL: {url}")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req) as resp:
            return resp.read()
    except Exception as e:
        print(f"[ERROR] Fetch error: {e}")
        raise


def parse_card(card: Tag) -> dict:
    """각 검색 카드에서 필요한 정보만 추출"""
    # Detail URL
    a_detail = card.select_one("a[href*='/content/']")
    detail_url = urljoin(BASE_URL, a_detail["href"]) if a_detail else None

    # Course Name
    title_el = card.select_one(".st--title h2")
    course_name = title_el.get_text(strip=True) if title_el else None

    #Section Name
    section_el = card.select_one(".st--section-name")
    section_name = section_el.get_text(strip=True) if section_el else None

    # Professor
    prof_el = card.select_one(".st--instructors")
    professor = prof_el.get_text(strip=True) if prof_el else None

    # Days
    days_el = card.select_one(".st--meeting-days span:last-of-type")
    days = days_el.get_text(strip=True) if days_el else None

    # Time
    time_el = card.select_one(".st--meeting-time span:last-of-type")
    start_time = end_time = None
    if time_el:
        time_text = time_el.get_text(strip=True)
        if "–" in time_text:
            parts = [p.strip() for p in time_text.split("–")]
        else:
            parts = [p.strip() for p in time_text.split("-")]
        if len(parts) == 2:
            start_time, end_time = parts
        else:
            start_time = parts[0]

    return {
        "Course Name": course_name,
        "Section Name": section_name,
        "Professor": professor,
        "Days": days,
        "Start Time": start_time,
        "End Time": end_time,
        "Detail URL": detail_url,
    }


def parse_single_page(url: str):
    """검색 페이지 1페이지 파싱"""
    html_bytes = fetch_html(url)
    soup = BeautifulSoup(html_bytes, "html.parser")

    cards = soup.select("div.views-row article") or soup.find_all("article")
    print(f"[INFO] 발견한 카드 수: {len(cards)}")

    rows = [parse_card(c) for c in cards]
    print(rows)
    return rows


def crawl_with_pagination(url_template: str, start_page: int = 0, max_pages: int = 200):
    all_rows = []

    for page in range(start_page, max_pages + 1):
        print(f"\n[INFO] ==== page {page} ====")
        url = url_template.format(page=page)
        rows = parse_single_page(url)

        if not rows:
            print("[INFO] 더 이상 과목 없음. 종료.")
            break

        all_rows.extend(rows)
        print(f"[INFO] 누적 과목 수: {len(all_rows)}")

    return all_rows


if __name__ == "__main__":
    URL_TEMPLATE = (
        "https://classes.berkeley.edu/search/class?"
        "utm_source=PANTHEON_STRIPPED&f%5B0%5D=term%3A8576&page={page}"
    )

    rows = crawl_with_pagination(URL_TEMPLATE, start_page=0, max_pages=334)
    df = pd.DataFrame(rows)

    print("\n[CHECK] Sample 20 rows:")
    print(df.head(20).to_string(index=False))

    df.to_excel("berkeley_schedule_all.xlsx", index=False)
    print(f"\n[DONE] Total {len(df)} rows saved to berkeley_schedule_all.xlsx")
