"""
블로그 통합 SEO 대시보드 - Google Search Console 데이터 수집

매일 GitHub Actions에서 실행되어:
  1. results/daily_summary.csv  - 블로그별 일별 클릭/노출/CTR/평균순위 (최근 10일 구간을 매번 다시 받아와 덮어씀 - GSC 데이터는 며칠간 계속 보정되기 때문)
  2. results/top_queries.csv    - 블로그별 최근 28일 상위 검색어 스냅샷 (매 실행마다 통째로 새로 씀)
을 갱신한다.

한 블로그가 여러 도메인(예: 티스토리 기본 도메인 + 커스텀 도메인)에 걸쳐 있으면
"sites" 목록에 URL을 여러 개 넣으면 자동으로 합산해서 하나로 보여준다.

필요한 것: 서비스 계정 JSON 키 (GitHub Secret: GSC_SERVICE_ACCOUNT_JSON)
자세한 설정 방법은 SETUP.md 참고.
"""

import csv
import datetime
import json
import os
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# ---- 여기에 블로그를 등록하세요 ----
# sites: Search Console에 등록된 속성 URL 목록 (URL 접두어 속성이면 끝에 슬래시 포함, 도메인 속성이면 "sc-domain:example.com")
#        같은 블로그가 도메인을 여러 개 쓰면(예: 티스토리 기본 도메인 + 커스텀 도메인) 여기에 전부 나열 - 자동으로 합산됨
# name: 대시보드에 표시할 이름
# color_slot: 1~4 (대시보드 색상 배정용, dataviz 팔레트 순번)
SITES = [
    {"sites": ["https://sohwakjeong.tistory.com/", "https://sohwakjeong.com/"], "name": "소확정", "color_slot": 1},
    {"sites": ["https://gudoklab.tistory.com/"], "name": "월정액연구소", "color_slot": 2},
    {"sites": ["https://haegyeoliji.tistory.com/"], "name": "해결일지", "color_slot": 3},
    # IT tips 블로그는 도메인이 정해지면 아래 줄의 주석을 풀고 URL을 채워주세요.
    # {"sites": ["https://YOUR-IT-TIPS-BLOG.tistory.com/"], "name": "IT 팁 블로그", "color_slot": 4},
]

DAILY_CSV = os.path.join("results", "daily_summary.csv")
QUERIES_CSV = os.path.join("results", "top_queries.csv")

# GSC는 데이터가 확정되기까지 2~3일 걸리고 이후에도 며칠간 수치가 보정될 수 있어서,
# 매번 최근 며칠 구간을 다시 받아와 기존 값을 덮어쓴다.
BACKFILL_DAYS = 10
TOP_QUERY_WINDOW_DAYS = 28
TOP_QUERY_LIMIT = 25


def get_service():
    key_json = os.environ.get("GSC_SERVICE_ACCOUNT_JSON")
    if not key_json:
        print("GSC_SERVICE_ACCOUNT_JSON 환경변수가 없어요. GitHub Secret 설정을 확인해주세요.", file=sys.stderr)
        sys.exit(1)
    info = json.loads(key_json)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("searchconsole", "v1", credentials=credentials)


def query_search_analytics(service, site, start_date, end_date, dimensions, row_limit=1000):
    body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }
    resp = service.searchanalytics().query(siteUrl=site, body=body).execute()
    return resp.get("rows", [])


def load_existing_daily_rows():
    rows = {}
    if os.path.exists(DAILY_CSV):
        with open(DAILY_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows[(row["property"], row["date"])] = row
    return rows


def fmt(n, digits=None):
    return round(n, digits) if digits is not None else n


def weighted_position(entries):
    """entries: [(clicks, impressions, position), ...] -> 노출수 가중 평균 순위"""
    total_impr = sum(e[1] for e in entries)
    if not total_impr:
        return 0
    return sum(e[1] * e[2] for e in entries) / total_impr


def main():
    service = get_service()
    today = datetime.date.today()

    existing = load_existing_daily_rows()

    # ---- 일별 요약 (블로그당 도메인 여러 개면 합산) ----
    for group in SITES:
        name = group["name"]
        start = today - datetime.timedelta(days=BACKFILL_DAYS)
        end = today - datetime.timedelta(days=1)  # 오늘 데이터는 아직 없으므로 어제까지

        # date -> [(clicks, impressions, position), ...] (도메인별 원시 값 모음)
        per_date = {}
        for site in group["sites"]:
            try:
                rows = query_search_analytics(service, site, start, end, dimensions=["date"])
            except Exception as e:
                print(f"[경고] {name} ({site}) 일별 데이터 수집 실패: {e}", file=sys.stderr)
                rows = []
            for r in rows:
                date_str = r["keys"][0]
                per_date.setdefault(date_str, []).append((
                    int(r.get("clicks", 0)),
                    int(r.get("impressions", 0)),
                    r.get("position", 0),
                ))

        for date_str, entries in per_date.items():
            clicks = sum(e[0] for e in entries)
            impressions = sum(e[1] for e in entries)
            ctr = (clicks / impressions * 100) if impressions else 0
            position = weighted_position(entries)
            existing[(name, date_str)] = {
                "property": name,
                "date": date_str,
                "clicks": clicks,
                "impressions": impressions,
                "ctr": fmt(ctr, 2),
                "position": fmt(position, 1),
            }
        print(f"{name}: 일별 데이터 {len(per_date)}일 갱신 (도메인 {len(group['sites'])}개 합산)")

    os.makedirs("results", exist_ok=True)
    with open(DAILY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["property", "date", "clicks", "impressions", "ctr", "position"])
        writer.writeheader()
        for key in sorted(existing.keys(), key=lambda k: (k[0], k[1])):
            writer.writerow(existing[key])

    # ---- 상위 검색어 스냅샷 (최근 28일, 도메인별 결과를 검색어 기준으로 합산 후 새로 씀) ----
    query_start = today - datetime.timedelta(days=TOP_QUERY_WINDOW_DAYS)
    query_end = today - datetime.timedelta(days=1)
    query_rows = []

    for group in SITES:
        name = group["name"]

        # query -> [(clicks, impressions, position), ...]
        per_query = {}
        for site in group["sites"]:
            try:
                rows = query_search_analytics(service, site, query_start, query_end, dimensions=["query"], row_limit=1000)
            except Exception as e:
                print(f"[경고] {name} ({site}) 검색어 데이터 수집 실패: {e}", file=sys.stderr)
                rows = []
            for r in rows:
                q = r["keys"][0]
                per_query.setdefault(q, []).append((
                    int(r.get("clicks", 0)),
                    int(r.get("impressions", 0)),
                    r.get("position", 0),
                ))

        merged = []
        for q, entries in per_query.items():
            clicks = sum(e[0] for e in entries)
            impressions = sum(e[1] for e in entries)
            ctr = (clicks / impressions * 100) if impressions else 0
            position = weighted_position(entries)
            merged.append({
                "generated_date": today.isoformat(),
                "property": name,
                "query": q,
                "clicks": clicks,
                "impressions": impressions,
                "ctr": fmt(ctr, 2),
                "position": fmt(position, 1),
            })

        merged.sort(key=lambda r: r["clicks"], reverse=True)
        query_rows.extend(merged[:TOP_QUERY_LIMIT])
        print(f"{name}: 상위 검색어 {min(len(merged), TOP_QUERY_LIMIT)}개 갱신 (도메인 {len(group['sites'])}개 합산)")

    with open(QUERIES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["generated_date", "property", "query", "clicks", "impressions", "ctr", "position"])
        writer.writeheader()
        writer.writerows(query_rows)

    print("완료.")


if __name__ == "__main__":
    main()
