# trend-master

한국 유튜브 인기 급상승 동영상을 수집해 마케팅 관점 카테고리로 분류하고, 이번 주 카테고리별 top5를 신문 스타일 웹 리포트로 발행하는 개인용 자동화 파이프라인.

- PRD: [`PRD.md`](./PRD.md)
- 설계/계획 문서: [`docs/superpowers/specs`](./docs/superpowers/specs), [`docs/superpowers/plans`](./docs/superpowers/plans)

## 동작 방식

```
유튜브 인기 급상승(KR) 수집
  → 영상별 상위 댓글 수집
  → Claude로 카테고리 분류(7종) + 2~3문장 요약 생성
  → SQLite 저장
  → 이번 주 카테고리별 조회수 top5로 리포트(docs/index.html) 생성
  → GitHub Pages 자동 배포 (REPORT_BASE_URL 설정 시)
  → 슬랙 알림 발송 (SLACK_WEBHOOK_URL 설정 시)
```

스케줄링 없이 **수동 실행**으로 동작한다 (`python run_pipeline.py` 또는 `/auto-report` 스킬).

## 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. `.env` 설정

`.env.example`을 복사해 `.env`를 만들고 값을 채운다.

```bash
cp .env.example .env
```

| 변수 | 필수 여부 | 설명 |
|---|---|---|
| `YOUTUBE_API_KEY` | 필수 | [Google Cloud Console](https://console.cloud.google.com)에서 YouTube Data API v3용 **API 키** 발급 (OAuth 클라이언트 아님) |
| `ANTHROPIC_API_KEY` | 필수 | [console.anthropic.com](https://console.anthropic.com)에서 발급, Billing에 결제 수단 등록 필요 |
| `REPORT_BASE_URL` | 선택 | 리포트가 배포될 GitHub Pages URL (예: `https://<user>.github.io/<repo>/`). 비워두면 배포·슬랙 알림 단계를 건너뜀 |
| `SLACK_WEBHOOK_URL` | 선택 | [Slack Incoming Webhook](https://api.slack.com/apps) URL. 비워두면 슬랙 알림을 건너뜀 |
| `YOUTUBE_REGION_CODE` | 선택 | 기본값 `KR` |
| `YOUTUBE_MAX_RESULTS` | 선택 | 기본값 `25` |
| `TREND_PIPELINE_DB_PATH` | 선택 | 기본값 `trend_pipeline.db` |
| `TREND_PIPELINE_REPORT_PATH` | 선택 | 기본값 `docs/index.html` |

### 3. GitHub Pages 배포 연결 (선택)

리포트를 웹에서 보려면 별도로 한 번 설정이 필요하다. 자세한 순서는 [`docs/superpowers/plans/2026-09-15-web-report-slack-notify.md`](./docs/superpowers/plans/2026-09-15-web-report-slack-notify.md)의 Task 6 참고.

1. 이 저장소를 GitHub에 **public**으로 push
2. 저장소 Settings → Pages → Source를 `master`(또는 `main`) 브랜치 `/docs` 폴더로 지정
3. `.env`의 `REPORT_BASE_URL`을 Pages URL로 채움

### 4. 실행

```bash
python run_pipeline.py
```

실행이 끝나면 콘솔에 각 단계 결과가 출력된다.

```
유튜브 수집: 25건
콘텐츠 분석: 성공 25건 / 실패 0건
리포트 배포: 성공
슬랙 알림: 성공
```

## 테스트

```bash
pytest -q
```

커밋 시 `.claude/hooks/pytest-gate.sh`가 pytest를 자동 실행해 실패하는 커밋을 막는다.

## 프로젝트 구조

```
trend_pipeline/
  categories.py        # 카테고리 상수 (7종), 분류·리포트 양쪽에서 공유
  youtube_collector.py # 유튜브 인기 급상승 수집 + 댓글 수집
  content_analyzer.py  # Claude로 카테고리 분류 + 요약 생성
  storage.py            # SQLite 저장/조회
  report_generator.py  # 카테고리 탭 신문 스타일 HTML 리포트 생성
  git_publisher.py     # 리포트 git add/commit/push 자동 배포
  slack_notifier.py    # 슬랙 웹훅 알림
  config.py             # .env 기반 설정 로딩
run_pipeline.py         # 전체 파이프라인 진입점
docs/index.html         # 생성된 최신 리포트 (GitHub Pages로 서빙)
```
