# Funding Story AI dev 배포 준비

이 Kustomization은 ServiceAccount, 내부 ClusterIP Service, 비밀키 없는 Google WIF `external_account` 설정 ConfigMap만 선언합니다. API·worker Pod, DB, Secret, projected token, 외부 경로는 생성하지 않습니다. API Deployment가 아래 Service의 selector를 사용하기 전까지는 엔드포인트가 없습니다. Project 서비스의 AI 호출 설정도 아직 변경하지 않습니다.

API·worker 매니페스트는 [`draft/`](draft/)에서 비활성 초안으로 관리합니다. 실제 배포 전 조건이 충족되기 전까지 상위 Kustomization에 연결하지 않습니다.

## EKS 신원과 내부 주소

- EKS OIDC issuer: `https://oidc.eks.ap-northeast-2.amazonaws.com/id/F9803D0BA6D1AF7F02C6DCB6AC3CB308`
- namespace: `dev`
- ServiceAccount: `funding-story-ai`
- OIDC subject: `system:serviceaccount:dev:funding-story-ai`
- API와 worker 3종은 같은 ServiceAccount를 사용합니다.
- API 내부 주소: `http://fundit-ai-funding-story-svc:8000` — API Pod의 `app.kubernetes.io/name: fundit-ai-funding-story` label과 `http` named port가 필요합니다.

## Project ↔ Funding Story 연동 계약

| 위치 | 환경변수 | 값 또는 출처 |
| --- | --- | --- |
| Project | `FUNDING_STORY_AI_BASE_URL` | `http://fundit-ai-funding-story-svc:8000` (BE 코드가 `/api/v1/ai`를 추가하므로 base path를 포함하지 않음) |
| Project / AI | `FUNDING_STORY_AI_SERVICE_TOKEN` / `AI_SERVICE_TOKEN` | 새 공유 Secret의 동일한 값. Secret은 아직 만들지 않음 |
| AI | `PROJECT_SERVICE_BASE_URL` | `http://fundit-project-svc:8080` |
| AI | `INTERNAL_API_KEY` | 기존 `fundit-backend-secrets/internal-api-key` 참조 |

Google Vertex AI는 EKS WIF용 `external_account` 설정을 ADC로 읽고, OpenAI는 별도 EKS WIF projected token을 사용합니다. 두 Provider의 audience와 토큰 파일 경로를 분리하며 Google 서비스 계정 private key JSON과 OpenAI API key는 배포하지 않습니다. 인증값·토큰 원문은 Git에 저장하지 않습니다.

## Pod 배포 시 WIF 마운트 계약

- API와 worker 3종 모두 `funding-story-ai` ServiceAccount를 사용하고 자동 ServiceAccount 토큰 마운트는 비활성화합니다.
- Google 전용 projected token의 audience는 `https://iam.googleapis.com/projects/254172583499/locations/global/workloadIdentityPools/funding-story-dev/providers/eks-dev`이며 `/var/run/secrets/google-identity/token`에 읽기 전용으로 마운트합니다.
- `funding-story-ai-google-wif` ConfigMap의 `credentials.json`을 `/var/run/secrets/google-wif/credentials.json`에 읽기 전용으로 마운트하고 `GOOGLE_APPLICATION_CREDENTIALS`를 해당 경로로 설정합니다.
- OpenAI 전용 projected token의 audience는 `https://api.openai.com/v1`이며 `/var/run/secrets/openai-wif/token`에 읽기 전용으로 마운트하고 `OPENAI_WIF_TOKEN_FILE`을 해당 경로로 설정합니다.
- 비루트 프로세스가 세 파일을 읽을 수 있는지, 실제 EKS에서 Google·OpenAI 단기 인증이 성공하는지 배포 후 검증합니다. ConfigMap만 적용한 현재 상태에서는 인증이 검증되지 않습니다.

## 실제 배포 전 조건

1. AI팀 문서상 Google·OpenAI WIF 신뢰 설정은 완료됐지만 실제 EKS 호출은 미검증입니다. 전달된 provider/service-account ID를 배포 시 사용하고 비루트 AI 이미지에서 projected token 파일을 읽을 수 있도록 Pod security context와 파일 권한을 검증합니다.
2. CNPG 담당자와 AI 전용 논리 DB·계정, 백업 지점, Flyway Job 실행 방식을 확정합니다. AI 저장소의 `db/migration` SQL은 runtime 이미지에 포함되지 않으며, 별도 Flyway Job에서 제공합니다.
3. 공유 서비스 토큰의 생성·관리 주체를 확정하고 Secret을 준비합니다. AI Deployment·Service의 준비 상태가 확인되기 전에는 Project의 AI 주소·토큰 환경변수를 반영하지 않습니다.
4. API Deployment·worker 3종·마이그레이션 Job·Secret 참조·readiness를 별도 GitOps PR로 추가합니다. ECR 이미지 tag/digest를 검증하고 Flyway migrate → validate → API·worker rollout → `/health/ready` → Project → AI smoke test 순서로 확인합니다.
