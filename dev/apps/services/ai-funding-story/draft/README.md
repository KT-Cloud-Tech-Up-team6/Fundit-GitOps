# Funding Story AI 워크로드 초안 (비활성)

상위 `../kustomization.yaml`에서 이 디렉터리를 참조하지 않으므로 Argo CD는 API·worker를 생성하지 않습니다. `kubectl kustomize dev/apps/services/ai-funding-story/draft`로 렌더링만 검증합니다. API 1개와 worker lane 3개(`funding-story`, `page-summary`, `storyline`)는 AI팀 `main`의 실행 명령을 따릅니다.

## 배포 전 필수 확인

1. AI팀 ECR의 실제 tag와 digest를 확인하고 API·worker 이미지의 `REPLACE_WITH_VERIFIED_TAG`를 같은 검증된 `tag@digest`로 교체합니다. 현재 값은 배포용 이미지가 아닙니다.
2. CNPG 담당자와 AI 논리 DB·계정, Flyway Job 및 migration 완료 게이트를 확정합니다. `funding-story-ai-db` Secret 이름과 `host`, `port`, `dbname`, `username`, `password` 키는 초안이며 실제 구성에 맞춰 조정합니다. Flyway 성공·validate 전에는 이 Kustomization을 상위에 연결하지 않습니다.
3. BE–AI 공유 토큰 소유자를 확정하고 `funding-story-ai-auth/service-token` Secret을 준비합니다. AI의 `AI_SERVICE_TOKEN`과 Project의 `FUNDING_STORY_AI_SERVICE_TOKEN`은 같은 값을 참조해야 합니다. 토큰 원문은 Git에 넣지 않습니다.
4. API·worker 4개 프로세스의 DB 연결 예산과 CPU·메모리 요청/제한, 비루트 파일 읽기 권한을 확정합니다. 이 초안에는 아직 리소스 크기를 지정하지 않았습니다.
5. 상위 Kustomization 연결 전에 Google·OpenAI projected token의 audience/권한, ConfigMap의 ADC 경로, API `/health/ready`, worker 프로세스 상태를 검증합니다. 현재 내부 Service는 API label만 선택해야 하므로 worker의 `app.kubernetes.io/name`을 다르게 지정했습니다.
6. API 준비와 실제 AI 호출이 확인된 뒤 Project의 `FUNDING_STORY_AI_BASE_URL=http://fundit-ai-funding-story-svc:8000` 및 공유 토큰 참조를 별도로 반영합니다. dev에서만 내부 HTTP 주소를 사용하며 prod HTTPS 정책은 별도입니다.

이 초안의 Google WIF ConfigMap 참조는 상위 Kustomization에 이미 병합된 `funding-story-ai-google-wif`를 사용합니다. API·worker는 동일한 `funding-story-ai` ServiceAccount를 쓰되 Google·OpenAI 토큰을 서로 다른 audience로 투영합니다.
