# Funding Story AI dev 신원 준비

AI팀의 EKS 인증 예시에 맞춰 dev API와 worker 3종이 동일한 Kubernetes ServiceAccount `funding-story-ai`를 사용하도록 신원을 예약합니다. 이 디렉터리는 현재 ServiceAccount만 적용하며 Pod, 이미지, DB, Secret, projected token, 외부 경로를 생성하지 않습니다.

AI팀·인증 관리자에게 전달할 공개 신원 정보:

- EKS OIDC issuer: `https://oidc.eks.ap-northeast-2.amazonaws.com/id/F9803D0BA6D1AF7F02C6DCB6AC3CB308`
- namespace: `dev`
- ServiceAccount: `funding-story-ai`
- OIDC subject: `system:serviceaccount:dev:funding-story-ai`
- API와 worker 3종은 동일한 ServiceAccount를 사용합니다. OpenAI WIF용 projected token은 별도 audience와 마운트 경로를 사용합니다.

Pod에는 자동 ServiceAccount 토큰을 마운트하지 않고, OpenAI WIF 설정이 확정된 뒤 해당 audience의 projected token만 추가합니다. Google 인증은 전용 서비스 계정 JSON key를 Kubernetes Secret으로 읽기 전용 마운트하는 방안이 제안됐으며, 보안 검토와 AI 코드·문서 변경이 선행되어야 합니다. 인증값이나 토큰 원문은 Git에 보관하지 않습니다.

## 실제 배포 전 조건

1. AI팀 `main`의 ECR `fundit-ai-funding-story` 이미지 push는 성공했습니다. 배포 PR에서 검증한 tag/digest로 고정합니다.
2. OpenAI WIF 신뢰 설정과 provider/service-account ID 및 audience를 확정합니다. Google 서비스 계정 JSON key 방식으로 전환한다면 AI팀이 `auth_check`의 `external_account` 전용 검사를 수정하고, GCP 계정 관리자가 전용 key를 안전하게 전달해야 합니다.
3. CNPG에 AI 전용 논리 DB·계정과 Flyway 마이그레이션 실행 경로 준비. 현재 AI Dockerfile에는 `db/migration`이 포함되지 않아 별도 마이그레이션 방법이 필요합니다.
4. API와 worker의 DB·서비스 토큰 Secret, BE 연결 주소를 확정. AI 문서의 BE 변수명 `FUNDING_STORY_AI_TOKEN`과 현재 project-service 코드의 `FUNDING_STORY_AI_SERVICE_TOKEN`이 달라 코드 기준으로 맞춰야 합니다.
5. 이후 별도 GitOps PR에서 Deployment·Service·worker·마이그레이션·Secret 참조·readiness를 추가하고 실제 연동을 검증.
