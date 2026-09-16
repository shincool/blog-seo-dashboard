# 블로그 SEO 대시보드 - 설정 가이드

데일리 트렌드 대시보드(`daily-trends` 저장소)와 구조가 같아요. GitHub Actions가 매일 자동으로
Search Console 데이터를 받아와 `results/` 폴더에 저장하고, `index.html`이 그 데이터를 읽어 그려줍니다.

## 1. 새 GitHub 저장소 만들기

`blog-seo-dashboard` 같은 이름으로 새 저장소를 만들고, 이 폴더에 있는 파일들을 그대로 커밋하세요
(`index.html`, `fetch_search_console.py`, `.github/workflows/seo-dashboard.yml`).

## 2. Google Cloud에서 서비스 계정 만들기 (한 번만 하면 돼요)

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 하나 만들거나 기존 걸 사용하세요.
2. 왼쪽 메뉴 "API 및 서비스" → "라이브러리"에서 **Search Console API**를 검색해 사용 설정하세요.
3. "API 및 서비스" → "사용자 인증 정보" → "사용자 인증 정보 만들기" → "서비스 계정"을 선택해 새 서비스 계정을 만드세요. (역할은 지정 안 해도 됩니다 - Search Console 권한은 3단계에서 별도로 줘요.)
4. 만든 서비스 계정 목록에서 방금 만든 계정을 클릭 → "키" 탭 → "키 추가" → "새 키 만들기" → JSON 선택. JSON 파일이 다운로드돼요. **이 파일이 비밀번호나 마찬가지니 남에게 공유하거나 저장소에 직접 커밋하면 안 돼요.**
5. 다운로드한 JSON 파일을 열어보면 `"client_email": "xxxxx@xxxxx.iam.gserviceaccount.com"` 같은 줄이 있어요. 이 이메일 주소를 복사해두세요.

## 3. 각 블로그를 Search Console에서 서비스 계정에 공유하기

이미 각 블로그를 Search Console에 속성으로 등록해두셨을 텐데, 거기에 서비스 계정을 "사용자"로 추가해야 해요.

1. [Search Console](https://search.google.com/search-console)에서 블로그 속성(예: 소확정) 선택
2. 왼쪽 메뉴 맨 아래 "설정" → "사용자 및 권한"
3. "사용자 추가" → 2단계에서 복사해둔 서비스 계정 이메일 입력 → 권한은 "전체" 대신 **"제한됨"**이면 충분해요 (읽기만 하면 되니까요)
4. 소확정 · 월정액연구소 · 해결일지(그리고 나중에 IT tips 블로그까지) 모두 같은 방식으로 추가

## 4. GitHub 저장소에 비밀 키 등록하기

1. 저장소 페이지에서 Settings → Secrets and variables → Actions → "New repository secret"
2. Name: `GSC_SERVICE_ACCOUNT_JSON`
3. Value: 2단계에서 다운로드한 JSON 파일의 내용을 **통째로** 복사해서 붙여넣기
4. Save

## 5. 첫 실행

Actions 탭 → "Daily Search Console Fetch" 워크플로 선택 → "Run workflow" 버튼으로 한 번 수동 실행해보세요.
초록색 체크가 뜨면 `results/daily_summary.csv`, `results/top_queries.csv`가 저장소에 생성돼요.
그 다음부터는 매일 자동으로 실행됩니다 (한국시간 오전 9시경).

## 6. 대시보드 보기

daily-trends 때처럼 저장소 Settings → Pages에서 main 브랜치를 소스로 지정하면
`https://[아이디].github.io/blog-seo-dashboard/` 에서 바로 볼 수 있어요.

## 참고

- `fetch_search_console.py` 맨 위 `SITES` 목록에 블로그가 등록돼 있어요. IT tips 블로그 도메인이 정해지면
  주석 처리된 줄의 URL을 채우고 주석을 풀어주시면 돼요.
- Search Console 속성 URL 형식이 다르면 (예: 도메인 속성으로 등록하신 경우) `"site"` 값을 `"sc-domain:example.com"` 형태로 바꿔주세요. Search Console 속성 목록 화면에서 정확한 형식을 확인할 수 있어요.
- 서치콘솔 데이터는 2~3일 지연되고 이후 며칠간 계속 보정되기 때문에, 스크립트가 매번 최근 10일치를 다시 받아와 갱신해요. 최신 1~2일 수치는 나중에 조금 바뀔 수 있어요.
