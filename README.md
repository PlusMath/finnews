# finnews

네이버 뉴스 검색 API(NAVER API HUB)로 경제 · 부동산 · 안전 키워드 뉴스를 **매시간 자동 수집**하고, 매일 09:00 KST에 직전 24시간 중 **중요도 상위 10건**(카테고리별)을 뽑아 정적 웹 리포트(`index.html`)로 보여주는 저장소입니다. 전 과정이 GitHub Actions로 자동화되어 있습니다.

## 동작 방식

```
매시간 (:05)  ─ collect_hourly.yml → scripts/collect_hourly.py
                 경제/부동산/안전사고 최신 뉴스를 조회해 data/buffer.json에 누적 (중복 제거, 48시간 보관)

매일 09:00 KST ─ summarize_daily.yml → scripts/summarize_daily.py
                 buffer.json에서 최근 24시간을 추려 카테고리별 상위 10건을 data/archive.json에 기록

상시            ─ index.html이 data/archive.json을 fetch로 읽어 날짜 선택 UI로 표시
```

네이버 검색 API는 특정 과거 날짜를 지정해 조회하는 기능이 없고, `start` 파라미터도 최대 1000까지만 지원합니다. "경제" 같은 넓은 키워드는 실시간으로 분당 수십 건씩 쏟아져 한 번의 호출로는 최근 1~2시간치 이상을 확보할 수 없기 때문에, **매시간 수집해 버퍼에 쌓는 방식**으로 24시간 커버리지를 확보합니다.

## 중요도 선정 기준

같은 이슈를 다루는 기사가 여러 개면 하나의 클러스터로 묶은 뒤(제목 토큰 유사도 기반), 클러스터마다 아래 점수로 순위를 매겨 카테고리별 상위 10개만 남깁니다.

```
점수 = 언론사 체급 점수 + min(보도 매체 수 − 1, 5) × 2

언론사 체급: 통신사 · 방송사(연합뉴스, KBS, YTN 등) = 5
             주요 종합지 · 경제지(조선, 중앙, 한겨레, 한국경제, 매일경제 등) = 3
             그 외 = 1
```

매체 목록은 `scripts/common.py`의 `OUTLETS` 딕셔너리에서 관리합니다. 없는 도메인은 자동으로 체급 1(그 외)로 처리됩니다.

## 구조

```
data/buffer.json          매시간 누적되는 원본 뉴스 버퍼 (최근 48시간, 자동 정리)
data/archive.json         날짜별 "카테고리별 상위 10건" 아카이브 (누적 저장)
scripts/common.py         API 호출/텍스트 정리/언론사 체급/클러스터링 공용 함수
scripts/collect_hourly.py 매시간 수집 스크립트
scripts/summarize_daily.py 매일 요약 스크립트
scripts/fetch_naver_news.sh 로컬에서 원본을 즉석으로 확인해보고 싶을 때 쓰는 수동 스크립트 (자동화 파이프라인과 별개)
.github/workflows/        GitHub Actions 정의 (매시간 수집, 매일 요약)
index.html                날짜 선택 가능한 정적 리포트 페이지
.env.example               로컬 실행용 API 인증 정보 템플릿
```

## 초기 설정 (필수)

이 저장소는 **public**이라 API 키를 코드에 커밋하지 않습니다. GitHub Actions가 쓸 수 있도록 저장소 Secrets에 등록해야 합니다.

1. GitHub 저장소 → **Settings → Secrets and variables → Actions → New repository secret**
   - `NCP_API_KEY_ID`: [developers.naver.com](https://developers.naver.com)에서 발급받은 Client ID
   - `NCP_API_KEY`: 같은 앱의 Client Secret
   - (NAVER API HUB 이전 이후 헤더명이 `X-NCP-APIGW-API-KEY-ID` / `X-NCP-APIGW-API-KEY`로 바뀌었습니다)
2. **Settings → Actions → General → Workflow permissions**에서 **"Read and write permissions"**를 선택해야 워크플로우가 결과를 자동 커밋/푸시할 수 있습니다.
3. 최초 1회 **Actions** 탭 → `Collect hourly news` → `Run workflow`로 수동 실행해 버퍼를 채운 뒤, `Summarize daily top10`도 한 번 수동 실행하면 바로 `data/archive.json`이 만들어집니다. 이후로는 스케줄대로 자동 실행됩니다.

## 로컬에서 원본만 빠르게 보고 싶을 때

```bash
cp .env.example .env   # 값 채우기
./scripts/fetch_naver_news.sh
```

`scripts/raw/raw_경제.json` 등 원본 JSON이 생성됩니다 (자동 파이프라인과는 별개의 수동 확인용).

## 리포트 로컬 확인

```bash
python -m http.server 8000
```

후 `http://localhost:8000` 접속. (파일을 직접 `file://`로 열면 브라우저가 `fetch`로 `data/archive.json`을 읽지 못합니다.)

## GitHub Pages

Settings → Pages에서 `main` 브랜치 루트를 소스로 지정하면 `index.html`이 그대로 배포되어 날짜별 리포트를 웹에서 바로 볼 수 있습니다.

## 데이터 형식 (`data/archive.json`)

```json
{
  "YYYY-MM-DD": {
    "generatedAt": "ISO8601 타임스탬프",
    "windowStart": "ISO8601 (수집 구간 시작)",
    "windowEnd": "ISO8601 (수집 구간 끝)",
    "economy": [
      { "time": "HH:MM", "title": "", "snippet": "", "source": "", "link": "", "coverage": 1, "score": 5 }
    ],
    "realestate": [ ... ],
    "safety": [ ... ]
  }
}
```

`coverage`는 같은 이슈를 보도한 것으로 판단된 매체 수, `score`는 그 이슈의 중요도 점수(최대 15)입니다.
