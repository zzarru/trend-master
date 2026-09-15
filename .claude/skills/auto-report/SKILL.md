---
name: auto-report
description: 트렌드 수집 파이프라인(run_pipeline.py)을 실행해 유튜브 트렌드 수집 → 키워드 추출 → 오늘/이번 주 리포트 생성 → GitHub Pages 자동 배포(git push) → 슬랙 알림까지 한 번에 처리한다. "리포트 실행해줘", "트렌드 파이프라인 돌려줘", "오늘자 리포트 발행해줘", "/auto-report" 같은 요청에서 발동. 이 스킬로 실행하는 run_pipeline.py의 git commit/push는 사용자가 사전에 승인한 자동화 흐름(docs/superpowers/specs/2026-09-15-web-report-slack-notify-design.md 참고)이므로, 실행 전에 매번 별도로 git push 승인을 다시 묻지 않는다.
---

# Auto Report

`run_pipeline.py`를 실행해 트렌드 리포트를 발행하는 스킬.

## 전제

- 저장소 루트(`C:\Users\user\Desktop\pjt\ai-workflow`)에 `.env`가 있고 `YOUTUBE_API_KEY`, `ANTHROPIC_API_KEY`가 채워져 있어야 함 (필수)
- `REPORT_BASE_URL`, `SLACK_WEBHOOK_URL`이 `.env`에 없으면 리포트 생성까지만 하고 배포·슬랙 알림은 자동으로 건너뜀 (파이프라인 자체 동작, 에러 아님)

## 실행

저장소 루트에서 아래 명령을 그대로 실행한다.

```bash
python run_pipeline.py
```

- 이 스크립트는 유튜브 수집 → 키워드 추출 → SQLite 저장 → `docs/index.html` 리포트 생성 → (`REPORT_BASE_URL`이 설정돼 있으면) **git add/commit/push까지 자동 실행** → (push 성공 + `SLACK_WEBHOOK_URL` 설정 시) 슬랙 알림 발송까지 전부 스크립트 내부에서 처리한다.
- 이 git push는 `docs/superpowers/specs/2026-09-15-web-report-slack-notify-design.md` 설계 단계에서 사용자가 명시적으로 승인한 자동화 흐름이다. 스킬 실행 시 이 push에 대해 별도로 다시 승인을 구하지 않는다 (단, `git commit`/`git push` 자체가 셸 권한 프롬프트로 뜨면 그건 하네스 권한 설정에 따른 것이므로 정상적으로 응답한다).
- 스크립트가 실패해도(수집 실패, 키워드 추출 실패, 배포 실패, 슬랙 실패) 파이프라인은 끝까지 실행되고 콘솔에 각 단계 성공/실패가 출력된다 — 이건 설계상 의도된 동작이다.

## 완료 후 보고

콘솔 출력을 그대로 요약해서 사용자에게 전달한다.

```
유튜브 수집: N건
키워드 추출: 성공 N건 / 실패 N건
리포트 배포: 성공/건너뜀/실패
슬랙 알림: 성공/건너뜀/실패
```

- "리포트 배포: 성공"이면 `https://<github-username>.github.io/<repo-name>/` 링크를 함께 안내한다 (`REPORT_BASE_URL` 값과 동일).
- 실패 항목이 있으면 원인을 짧게 설명한다 (예: 키워드 추출 실패는 Anthropic 크레딧/일시적 API 오류일 수 있음, 배포 실패는 git 충돌/네트워크 문제일 수 있음 — 스크립트가 원인 메시지를 콘솔에 이미 출력하므로 그걸 인용).

## 하지 않는 것

- `.env` 파일을 직접 만들거나 수정하지 않는다 (이미 설정돼 있다고 가정; 없으면 사용자에게 알리고 중단)
- 코드나 파이프라인 로직을 수정하지 않는다 (이 스킬은 실행 전용)
- `docs/index.html` 외의 파일을 커밋하지 않는다 (스크립트가 이미 `report_path`만 스코프해서 커밋함)
