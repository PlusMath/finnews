"""매일 09:00 KST 실행: 최근 24시간 버퍼를 정리해 카테고리별 중요도 상위 10건을
data/archive.json에 오늘 날짜로 기록한다.

점수 = 언론사 체급(통신사/방송 5, 주요종합/경제지 3, 그 외 1) + min(보도매체수-1, 5) * 2
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import KST, QUERIES, cluster_items, jaccard, score_cluster

DEDUP_THRESHOLD = 0.5  # 1차 클러스터링을 통과한 뒤, 최종 상위 N 안에서 서로 겹치는 이슈를 한 번 더 거른다
DEDUP_ASSIST_THRESHOLD = 0.12
DEDUP_MIN_SHARED_DECIMALS = 2

ROOT = Path(__file__).parent.parent
BUFFER_PATH = ROOT / "data" / "buffer.json"
ARCHIVE_PATH = ROOT / "data" / "archive.json"
TOP_N = 10


def load_json(path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    buffer = load_json(BUFFER_PATH, {"items": []})
    now = datetime.now(KST)
    window_end = now
    window_start = now - timedelta(hours=24)

    windowed = [
        it for it in buffer["items"]
        if window_start <= datetime.fromisoformat(it["pubDate"]) < window_end
    ]

    by_category = {key: [] for key in QUERIES}
    for it in windowed:
        by_category.setdefault(it["category"], []).append(it)

    result = {}
    for category, items in by_category.items():
        clusters = cluster_items(items)
        scored = []
        for c in clusters:
            score, coverage = score_cluster(c)
            scored.append((score, coverage, c))
        scored.sort(key=lambda x: (x[0], x[1], x[2]["rep"]["pubDate"]), reverse=True)

        top = []
        picked = []  # list of (rep_shingles, rep_decimals)
        for score, coverage, c in scored:
            rep_shingles = c["rep_shingles"]
            rep_decimals = c["rep_decimals"]
            is_dup = any(
                jaccard(rep_shingles, s) >= DEDUP_THRESHOLD
                or len(rep_decimals & d) >= DEDUP_MIN_SHARED_DECIMALS
                or (len(rep_decimals & d) >= 1 and jaccard(rep_shingles, s) >= DEDUP_ASSIST_THRESHOLD)
                for s, d in picked
            )
            if is_dup:
                continue
            top.append((score, coverage, c))
            picked.append((rep_shingles, rep_decimals))
            if len(top) >= TOP_N:
                break
        result[category] = [
            {
                "time": datetime.fromisoformat(c["rep"]["pubDate"]).strftime("%H:%M"),
                "title": c["rep"]["title"],
                "snippet": c["rep"]["snippet"],
                "source": c["rep"]["source"],
                "link": c["rep"]["link"],
                "coverage": coverage,
                "score": score,
            }
            for score, coverage, c in top
        ]

    archive = load_json(ARCHIVE_PATH, {})
    date_key = window_end.strftime("%Y-%m-%d")
    archive[date_key] = {
        "generatedAt": window_end.isoformat(),
        "windowStart": window_start.isoformat(),
        "windowEnd": window_end.isoformat(),
        **result,
    }

    with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)

    for cat, items in result.items():
        print(f"{cat}: 후보 {len(by_category.get(cat, []))}건 -> 선정 {len(items)}건")


if __name__ == "__main__":
    main()
