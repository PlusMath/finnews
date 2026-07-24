"""매시간 실행: 3개 키워드 뉴스를 가져와 data/buffer.json에 누적한다.

사용법: NCP_API_KEY_ID=xxx NCP_API_KEY=yyy python scripts/collect_hourly.py
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import KST, QUERIES, clean_text, domain_of, fetch_page, outlet_of, parse_pubdate

ROOT = Path(__file__).parent.parent
BUFFER_PATH = ROOT / "data" / "buffer.json"
MAX_PAGES = 10       # display=100 * 10 = 최대 1000건/키워드/회
STALE_MARGIN_MIN = 70  # 최근 70분보다 오래된 페이지가 나오면 조기 종료
KEEP_HOURS = 48       # 버퍼 보관 기간


def load_buffer():
    if BUFFER_PATH.exists():
        with open(BUFFER_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"items": []}


def fetch_keyword(category, query, key_id, key_secret):
    now = datetime.now(KST)
    collected = []
    for page in range(MAX_PAGES):
        start = page * 100 + 1
        try:
            data = fetch_page(query, key_id, key_secret, display=100, start=start)
        except Exception as e:
            print(f"[warn] {category} page {page+1} 요청 실패: {e}", file=sys.stderr)
            break
        items = data.get("items", [])
        if not items:
            break
        oldest_on_page = None
        for raw in items:
            pub = parse_pubdate(raw["pubDate"])
            oldest_on_page = pub if oldest_on_page is None or pub < oldest_on_page else oldest_on_page
            domain = domain_of(raw)
            collected.append({
                "category": category,
                "pubDate": pub.isoformat(),
                "title": clean_text(raw["title"]),
                "snippet": clean_text(raw["description"]),
                "domain": domain,
                "source": outlet_of(domain)[0],
                "link": raw.get("link") or raw.get("originallink"),
            })
        if oldest_on_page and (now - oldest_on_page) > timedelta(minutes=STALE_MARGIN_MIN):
            break
    return collected


def main():
    key_id = os.environ.get("NCP_API_KEY_ID")
    key_secret = os.environ.get("NCP_API_KEY")
    if not key_id or not key_secret:
        print("오류: NCP_API_KEY_ID / NCP_API_KEY 환경변수가 필요합니다.", file=sys.stderr)
        sys.exit(1)

    buffer = load_buffer()
    existing_links = {item["link"] for item in buffer["items"] if item.get("link")}

    total_new = 0
    any_success = False
    for category, query in QUERIES.items():
        fetched = fetch_keyword(category, query, key_id, key_secret)
        if fetched:
            any_success = True
        new_items = [it for it in fetched if it["link"] not in existing_links]
        for it in new_items:
            existing_links.add(it["link"])
        buffer["items"].extend(new_items)
        total_new += len(new_items)
        print(f"{category}: 조회 {len(fetched)}건, 신규 {len(new_items)}건")

    if not any_success:
        print("오류: 모든 키워드 조회에 실패했습니다.", file=sys.stderr)
        sys.exit(1)

    cutoff = datetime.now(KST) - timedelta(hours=KEEP_HOURS)
    buffer["items"] = [
        it for it in buffer["items"] if datetime.fromisoformat(it["pubDate"]) >= cutoff
    ]
    buffer["items"].sort(key=lambda it: it["pubDate"], reverse=True)

    BUFFER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BUFFER_PATH, "w", encoding="utf-8") as f:
        json.dump(buffer, f, ensure_ascii=False, indent=2)

    print(f"총 신규 {total_new}건 추가, 버퍼 보관 {len(buffer['items'])}건")


if __name__ == "__main__":
    main()
