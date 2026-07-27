#!/bin/bash
# NAVER API HUB 뉴스 검색 - 경제/부동산/안전사고/비트코인 원본 JSON 수집
#
# 사용법:
#   NCP_API_KEY_ID=xxx NCP_API_KEY=yyy ./scripts/fetch_naver_news.sh
#   또는 저장소 루트에 .env 파일(.env.example 참고)을 두면 자동으로 읽습니다.
#
# 결과: scripts/raw/raw_경제.json, raw_부동산.json, raw_안전사고.json, raw_비트코인.json
#
# 참고: Windows에서 curl에 한글 인자를 그대로 넘기면 코드페이지 변환 문제로
# EUC-KR로 잘못 인코딩되는 경우가 있어, UTF-8 percent-encoding을 미리 계산해 사용합니다.

set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$DIR/.env" ]; then
  set -a
  source "$DIR/.env"
  set +a
fi

if [ -z "${NCP_API_KEY_ID:-}" ] || [ -z "${NCP_API_KEY:-}" ]; then
  echo "오류: NCP_API_KEY_ID / NCP_API_KEY 환경변수가 설정되지 않았습니다." >&2
  echo "저장소 루트에 .env 파일을 만들거나 (.env.example 참고), 환경변수로 직접 넘겨주세요." >&2
  exit 1
fi

BASE="https://naverapihub.apigw.ntruss.com/search/v1/news"
OUT="$DIR/scripts/raw"
mkdir -p "$OUT"

declare -A Q
Q["경제"]="%EA%B2%BD%EC%A0%9C"
Q["부동산"]="%EB%B6%80%EB%8F%99%EC%82%B0"
Q["안전사고"]="%EC%95%88%EC%A0%84%EC%82%AC%EA%B3%A0"
Q["비트코인"]="%EB%B9%84%ED%8A%B8%EC%BD%94%EC%9D%B8"

for kw in "경제" "부동산" "안전사고" "비트코인"; do
  url="${BASE}?query=${Q[$kw]}&display=30&sort=date&format=json"
  curl -s "$url" \
    -H "X-NCP-APIGW-API-KEY-ID: $NCP_API_KEY_ID" \
    -H "X-NCP-APIGW-API-KEY: $NCP_API_KEY" \
    -o "$OUT/raw_${kw}.json"
  echo "saved: scripts/raw/raw_${kw}.json ($(wc -c < "$OUT/raw_${kw}.json") bytes)"
done
