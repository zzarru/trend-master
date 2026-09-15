# 웹 리포트 & 슬랙 알림 Design

## 개요

기존 MVP 트렌드 수집 파이프라인(`run_pipeline.py`)이 유튜브 트렌드 수집 → 키워드 추출 → SQLite 저장까지 완료한 뒤, 이어서 다음을 자동으로 수행한다.

1. SQLite에 쌓인 키워드/콘텐츠를 오늘/이번 주 기준으로 집계해 정적 HTML 리포트를 생성
2. 생성된 리포트를 GitHub Pages로 자동 배포(git add/commit/push)
3. 배포 완료 후 슬랙 Incoming Webhook으로 "리포트 준비됨: [링크]" 알림 1건 발송

PRD의 핵심 기능 2번("요약 리포트 — 오늘/이번 주 뜬 키워드 랭킹 + 대표 콘텐츠 링크 제공")과 비기능 요구사항("웹 대시보드 + 슬랙 요약 알림")을 만족한다.

## 전제 조건 (구현 전 사용자 액션 필요)

- 이 저장소를 GitHub에 **public**으로 새로 생성하고 push (현재 로컬에만 존재, remote 없음)
- 저장소 Settings → Pages에서 `main` 브랜치 `/docs` 폴더를 Pages 소스로 지정 (최초 1회, 수동)
- 슬랙 워크스페이스에 Incoming Webhook 앱 생성 후 Webhook URL 발급, `.env`에 `SLACK_WEBHOOK_URL`로 저장

## 아키텍처 & 구성요소

```
run_pipeline.py
  ├─ (기존) youtube_collector → storage.save_content
  ├─ (기존) keyword_extractor → storage.save_keywords
  ├─ (신규) report_generator.generate_report(conn, now) -> str (HTML)
  │         → docs/index.html 로 저장
  ├─ (신규) git_publisher.publish(paths, run=subprocess.run) → commit + push
  └─ (신규) slack_notifier.notify(webhook_url, report_url, post=requests.post)
```

- **`trend_pipeline/report_generator.py`**
  - `generate_report(conn: sqlite3.Connection, now: datetime) -> str`
  - SQLite에서 오늘/이번 주 키워드 빈도 집계 + 대표 콘텐츠 조인 → HTML 문자열 반환 (파일 I/O는 `run_pipeline.py`에서 처리)
- **`trend_pipeline/git_publisher.py`**
  - `publish(paths: list[str], commit_message: str, run=subprocess.run) -> bool`
  - `git add {paths} && git commit -m {commit_message} && git push` 순차 실행, 외부 명령 실행자를 인자로 주입받아 테스트 시 mock 가능
- **`trend_pipeline/slack_notifier.py`**
  - `notify(webhook_url: str, report_url: str, post=requests.post) -> bool`
  - `post(webhook_url, json={"text": f"오늘의 트렌드 리포트가 준비됐어요: {report_url}"})`

기존 컨벤션(외부 I/O는 인자로 주입, mock 가능)을 그대로 따른다.

## 데이터 흐름 & 리포트 내용

- 집계 기준 컬럼: `raw_content.collected_at`
  - **오늘**: 로컬 기준 오늘 날짜(00:00~현재)에 수집된 콘텐츠
  - **이번 주**: 이번 주 월요일 00:00 이후 수집된 콘텐츠
- 쿼리: `keywords JOIN raw_content ON keywords.content_id = raw_content.id`
  - `GROUP BY keyword`, `COUNT(*) DESC`로 정렬해 랭킹 산출
  - 각 키워드의 대표 콘텐츠는 해당 키워드가 달린 콘텐츠 중 `score`(조회수) 최댓값 1건
- HTML 구조 (섹션 2개, 정적 마크업):
  ```
  # 오늘의 트렌드 키워드
  1. AI 커버 (3건) — [대표 영상 제목](url)
  2. ...

  # 이번 주 트렌드 키워드
  1. ...
  ```
- 데이터가 0건인 구간은 "오늘 수집된 트렌드가 없습니다" 같은 빈 상태 문구로 대체 (빈 리스트로 KeyError/IndexError 나지 않도록 처리)

## 에러 처리

- `report_generator`는 DB에 데이터가 없어도 예외 없이 빈 리포트 HTML을 반환한다 (파이프라인 전체를 막지 않음).
- `git_publisher.publish()` 실패(네트워크 오류, push 충돌 등)는 예외를 잡아 콘솔에 로그만 남기고 파이프라인은 계속 진행한다. 리포트 파일은 로컬(`docs/index.html`)에 이미 생성돼 있으므로 배포 실패가 데이터 유실로 이어지지 않는다.
- `slack_notifier.notify()` 실패(webhook 오류)도 동일하게 예외를 잡아 로그만 남기고 파이프라인은 정상 종료한다.
- 에러 로그에 민감정보(webhook URL 등)가 노출되지 않도록 기존 `re.sub` 패턴으로 redact 처리한다.
- `run_pipeline.py`의 최종 요약 출력에 리포트 생성/배포/슬랙 알림 각각의 성공 여부를 1줄씩 추가한다.

## 테스트 계획

- `report_generator`: 오늘/이번 주 집계 로직(경계값 포함), 빈 데이터 케이스, 대표 콘텐츠 링크가 HTML에 포함되는지 — 실제 파일 I/O 없이 반환된 HTML 문자열을 검증
- `git_publisher`: `run` 인자에 mock을 주입해 올바른 git 명령이 순서대로 호출되는지, 실패 시 예외를 잡아 False를 반환하는지 검증
- `slack_notifier`: `post` 인자에 mock을 주입해 webhook URL과 메시지 payload가 올바른지, 실패 시 예외를 잡아 False를 반환하는지 검증
- `run_pipeline`: report_generator/git_publisher/slack_notifier가 각각 실패해도 파이프라인이 끝까지 실행되고 요약에 실패 상태가 반영되는지 통합 검증 (기존 `test_run_pipeline.py` 패턴 확장)

## 범위 제외 (Out of Scope)

- 리포트 페이지 접근 제어(로그인/비밀번호) — public GitHub Pages이므로 링크를 아는 사람은 누구나 접근 가능함을 인지하고 진행
- 슬랙 메시지의 리치 포맷(버튼, 첨부, 스레드 등) — 텍스트 링크 1줄만
- 스케줄링/자동 실행 — 기존과 동일하게 수동 실행(`python run_pipeline.py`)에 포함되는 후속 단계일 뿐
