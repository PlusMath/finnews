"""공용 유틸: NAVER API HUB 뉴스 검색 호출, 텍스트 정리, 언론사 체급, 클러스터링/점수."""
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

KST = timezone(timedelta(hours=9))

API_BASE = "https://naverapihub.apigw.ntruss.com/search/v1/news"

QUERIES = {
    "economy": "경제",
    "realestate": "부동산",
    "safety": "안전사고",
}

# domain -> (표시이름, tier)  tier: 5=통신사/방송사, 3=주요 종합지/경제지, 1=그 외
OUTLETS = {
    "yna.co.kr": ("연합뉴스", 5),
    "ytn.co.kr": ("YTN", 5),
    "kbs.co.kr": ("KBS", 5),
    "imbc.com": ("MBC", 5),
    "mbc.co.kr": ("MBC", 5),
    "sbs.co.kr": ("SBS", 5),
    "jtbc.co.kr": ("JTBC", 5),
    "news.jtbc.co.kr": ("JTBC", 5),
    "newsis.com": ("뉴시스", 5),
    "news1.kr": ("뉴스1", 5),
    "yonhapnewstv.co.kr": ("연합뉴스TV", 5),
    "chosun.com": ("조선일보", 3),
    "biz.chosun.com": ("조선비즈", 3),
    "joongang.co.kr": ("중앙일보", 3),
    "joins.com": ("중앙일보", 3),
    "donga.com": ("동아일보", 3),
    "hani.co.kr": ("한겨레", 3),
    "khan.co.kr": ("경향신문", 3),
    "hankyung.com": ("한국경제", 3),
    "mk.co.kr": ("매일경제", 3),
    "sedaily.com": ("서울경제", 3),
    "mt.co.kr": ("머니투데이", 3),
    "edaily.co.kr": ("이데일리", 3),
    "asiae.co.kr": ("아시아경제", 3),
    "view.asiae.co.kr": ("아시아경제", 3),
    "fnnews.com": ("파이낸셜뉴스", 3),
    "heraldcorp.com": ("헤럴드경제", 3),
    "biz.heraldcorp.com": ("헤럴드경제", 3),
    "koreaherald.com": ("코리아헤럴드", 3),
    "seoul.co.kr": ("서울신문", 3),
    "munhwa.com": ("문화일보", 3),
    "segye.com": ("세계일보", 3),
    "hankookilbo.com": ("한국일보", 3),
    "kmib.co.kr": ("국민일보", 3),
}


def clean_text(raw):
    """API가 주는 <b> 태그와 HTML 엔티티를 정리."""
    text = re.sub(r"</?b>", "", raw or "")
    return html.unescape(text).strip()


def fetch_page(query, key_id, key_secret, display=100, start=1):
    url = (
        f"{API_BASE}?query={urllib.parse.quote(query)}"
        f"&display={display}&start={start}&sort=date&format=json"
    )
    req = urllib.request.Request(
        url,
        headers={
            "X-NCP-APIGW-API-KEY-ID": key_id,
            "X-NCP-APIGW-API-KEY": key_secret,
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def domain_of(item):
    link = item.get("originallink") or item.get("link") or ""
    netloc = urlparse(link).netloc.lower()
    for prefix in ("www.", "m.", "n.", "news."):
        if netloc.startswith(prefix) and netloc != f"{prefix}naver.com":
            netloc = netloc[len(prefix):]
    return netloc


def outlet_of(domain):
    return OUTLETS.get(domain, (domain, 1))


def parse_pubdate(raw):
    dt = parsedate_to_datetime(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def normalize_title(title):
    t = re.sub(r"\[[^\]]*\]", " ", title)
    t = re.sub(r"[\"'“”‘’…·,.!?()\[\]{}<>~%:;\-–—]", " ", t)
    tokens = [tok for tok in t.split() if len(tok) >= 2]
    return set(tokens)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def cluster_items(items, threshold=0.45):
    """category 내 유사 제목 기사를 하나의 클러스터로 묶는다."""
    clusters = []  # list of dict: tokens, domains(set), rep(item with best tier), items(list)
    for item in items:
        tokens = normalize_title(item["title"])
        best = None
        best_sim = 0.0
        for c in clusters:
            sim = jaccard(tokens, c["tokens"])
            if sim > best_sim:
                best_sim = sim
                best = c
        if best is not None and best_sim >= threshold:
            best["domains"].add(item["domain"])
            best["items"].append(item)
            rep_tier = outlet_of(best["rep"]["domain"])[1]
            item_tier = outlet_of(item["domain"])[1]
            if item_tier > rep_tier:
                best["rep"] = item
            best["tokens"] = best["tokens"] | tokens
        else:
            clusters.append({
                "tokens": tokens,
                "domains": {item["domain"]},
                "items": [item],
                "rep": item,
            })
    return clusters


def score_cluster(cluster):
    _, tier = outlet_of(cluster["rep"]["domain"])
    coverage = len(cluster["domains"])
    return tier + min(coverage - 1, 5) * 2, coverage
