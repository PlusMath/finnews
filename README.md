# finnews

네이버 뉴스 검색 API(NAVER API HUB)로 경제 · 부동산 · 안전 키워드 뉴스를 수집해 날짜별로 쌓아두고, 정적 웹 리포트(`index.html`)로 보여주는 저장소입니다.

## 구조

```
data/archive.json        날짜별 뉴스 스냅샷 아카이브 (누적 저장)
scripts/fetch_naver_news.sh  NAVER API HUB에서 원본 뉴스 JSON을 가져오는 스크립트
scripts/raw/              스크립트 실행 결과 원본 JSON (선별 전 데이터)
index.html                날짜 선택 가능한 정적 리포트 페이지
.env.example              API 인증 정보 템플릿
```

## 인증 정보 설정

이 저장소는 **public**이므로 API 키를 코드에 커밋하지 않습니다. `.env.example`을 복사해 `.env`를 만들고 값을 채워주세요.

```
cp .env.example .env
```

- `NCP_API_KEY_ID`, `NCP_API_KEY`: [developers.naver.com](https://developers.naver.com) → 애플리케이션 등록 시 "검색" API를 선택해 발급받은 값 (NAVER API HUB 이전 이후 헤더명이 `X-NCP-APIGW-API-KEY-ID` / `X-NCP-APIGW-API-KEY`로 변경되었습니다)

## 사용법

1. 뉴스 원본 수집

   ```bash
   ./scripts/fetch_naver_news.sh
   ```

   `scripts/raw/raw_경제.json`, `raw_부동산.json`, `raw_안전사고.json`이 생성됩니다.

2. 원본 중 의미 있는 기사를 선별해 `data/archive.json`에 오늘 날짜 키로 추가합니다 (형식은 기존 항목 참고).

3. 리포트 확인

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
    "economy": [ { "time": "HH:MM", "title": "", "snippet": "", "source": "", "link": "" }, ... ],
    "realestate": [ ... ],
    "safety": [ ... ]
  }
}
```
