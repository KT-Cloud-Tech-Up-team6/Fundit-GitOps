# Funding Story AI dev 배포 준비

이 Kustomization은 ServiceAccount와 내부 ClusterIP Service만 선언합니다. API·worker Pod, DB, Secret, projected token, 외부 경로는 생성하지 않습니다. API Deployment가 아래 Service의 selector를 사용하기 전까지는 엔드포인트가 없습니다. Project 서비스의 AI 호출 설정도 아직 변경하지 않습니다.

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

## 실제 배포 전 조건

1. AI팀·인증 관리자가 Google·OpenAI WIF 신뢰 설정 및 provider/service-account ID를 확정합니다. 비루트 AI 이미지에서 projected token 파일을 읽을 수 있도록 Pod security context와 파일 권한을 검증합니다.
2. CNPG 담당자와 AI 전용 논리 DB·계정, 백업 지점, Flyway Job 실행 방식을 확정합니다. AI 저장소의 `db/migration` SQL은 runtime 이미지에 포함되지 않으며, 별도 Flyway Job에서 제공합니다.
3. 공유 서비스 토큰의 생성·관리 주체를 확정하고 Secret을 준비합니다. AI Deployment·Service의 준비 상태가 확인되기 전에는 Project의 AI 주소·토큰 환경변수를 반영하지 않습니다.
4. API Deployment·worker 3종·마이그레이션 Job·Secret 참조·readiness를 별도 GitOps PR로 추가합니다. ECR 이미지 tag/digest를 검증하고 Flyway migrate → validate → API·worker rollout → `/health/ready` → Project → AI smoke test 순서로 확인합니다.
