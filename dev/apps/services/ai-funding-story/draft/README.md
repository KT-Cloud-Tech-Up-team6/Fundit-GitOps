# Funding Story AI dev 배포

이 브랜치에서는 상위 `../kustomization.yaml`이 `migration/`과 `draft/`를 참조합니다. `main`에 병합되면 Argo CD `fundit-dev`가 Flyway PreSync Job을 먼저 실행하고, 성공한 뒤 API 1개와 worker 3개(`funding-story`, `page-summary`, `storyline`)를 배포합니다. 선택적 Sync는 훅을 건너뛸 수 있으므로 전체 Application Sync로 적용합니다.

## 2026-09-29 사전 준비

- CNPG 2/2 Ready, 최신 S3 전체 백업 완료, WAL 아카이브 정상. `funding_story_ai` 논리 DB는 UTF8/C.utf8로 생성했습니다.
- `funding_story_ai_migrator`는 DB 소유 및 DDL, `funding_story_ai_app`은 AI 데이터 테이블 DML과 `flyway_schema_history` SELECT만 허용합니다. 앱 계정의 TLS 접속과 권한을 검증했습니다.
- `dev/funding-story-ai-migration-db` (`url`, `username`, `password`), `dev/funding-story-ai-db` (`host`, `port`, `dbname`, `username`, `password`), `dev/funding-story-ai-auth` (`service-token`)를 등록했습니다. 값은 Git에 저장하지 않습니다.
- AI팀 `b93736a` 게시 로그에서 API와 migration 이미지의 태그·digest를 확인했습니다. migration 이미지는 클러스터가 받아 Flyway V1·V2 Job이 완료됐습니다. Argo CD의 PreSync Job 재실행은 Flyway의 적용 이력을 검증하고 이미 적용한 V1·V2는 건너뜁니다.
- API·worker 4개는 동일한 `funding-story-ai` ServiceAccount를 쓰며, Google·OpenAI 토큰은 서로 다른 audience로 투영합니다. Google external_account JSON은 비밀키가 없는 ConfigMap입니다.
- dev 초기 리소스 요청은 각 250m CPU/512Mi 메모리, 제한은 각 1 CPU/2Gi입니다. DB 연결 풀 상한은 프로세스당 일반 2 + checkpoint 1로 설정했습니다. 실제 부하 검증 후 조정합니다.

## 병합 후 확인

1. Argo CD 전체 Sync/Health, PreSync Job Complete, API `/health/ready`, worker 3개의 Ready 및 재시작 횟수를 확인합니다.
2. Pod에서 Google·OpenAI WIF 토큰 파일 읽기 및 실제 Provider 호출을 확인합니다. Pod Ready만으로 외부 AI 기능 성공을 판정하지 않습니다.
3. AI API가 정상일 때 Project에 `FUNDING_STORY_AI_BASE_URL=http://fundit-ai-funding-story-svc:8000`과 `FUNDING_STORY_AI_SERVICE_TOKEN`을 별도 GitOps 변경으로 연결합니다. Project와 AI의 `AI_SERVICE_TOKEN`은 같은 `funding-story-ai-auth/service-token`을 참조해야 합니다. 공통 `INTERNAL_API_KEY`는 기존 `fundit-backend-secrets`를 참조합니다.
4. PreSync 훅은 `fundit-dev` 전체 Sync마다 재실행됩니다. DB 접속 장애가 다른 서비스의 GitOps 변경까지 막을 수 있으므로, 초기 검증 후 훅의 상시 유지 또는 Funding Story 별도 Application 분리를 검토합니다.

실패 시 먼저 API·worker 활성화 리소스를 원복합니다. Flyway 마이그레이션과 DB 데이터는 자동으로 롤백되지 않으며, 복구가 필요하면 사전 백업과 별도 절차로 판단합니다.
