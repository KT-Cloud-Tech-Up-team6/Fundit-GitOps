# Live 배포 전제조건

`fundit-live`는 CNPG의 `app` 데이터베이스 안에서 `live` 스키마를 사용합니다.
Flyway가 스키마와 이력 테이블을 생성하며 다른 서비스의 migration과 분리됩니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.

## IVS 및 Kafka

현재 dev 배포는 `LIVE_IVS_MODE=stub`을 사용하므로 AWS IVS 자격증명이 필요하지 않습니다.
실제 IVS 연동은 AWS 담당자와 IAM 권한 및 선택 설정을 별도로 확정한 뒤 진행합니다.

## Live AI

현재 dev 배포는 `LIVE_AI_MODE=http`으로 Copilot Q&A AI와 Cuesheet AI를 함께 호출합니다.
ConfigMap에는 각 내부 Service URL을 설정하고, Deployment는 아래 기존 Secret key를 참조합니다.

- `fundit-ai-copilot-secret/api-token` → `LIVE_AI_TOKEN`
- `fundit-ai-cuesheet-secret/cuesheet-ai-token` → `LIVE_CUESHEET_AI_TOKEN`

두 AI는 서로 다른 서버·토큰을 사용합니다. 값은 Git, PR, 로그에 기록하지 않으며,
IVS는 이 변경과 무관하게 `stub`으로 유지합니다.

현재 이미지의 Live 서비스는 Kafka 이벤트를 발행만 하며 구독 토픽과 Redis 설정을 요구하지 않습니다.

## Gateway 경로

Gateway의 `LIVE_SERVICE_BASE_URL`은 `http://fundit-live-svc:8080`을 사용합니다.
외부 `/api/v1/lives/**` 요청은 Live 서비스로 전달되며 `/internal/v1/lives/**`는 노출하지 않습니다.

## 배포 이미지

Backend `develop`의 성공한 live-service 이미지가 GitOps 자동 갱신으로 반영됩니다.
현재 선언된 tag와 digest는 이 디렉터리의 `kustomization.yaml` `images` 항목에서 확인합니다.
실제 배포 이미지는 `dev/fundit-live` Deployment와 Pod의 `imageID`로 대조합니다.
이전 CI 커밋이나 실행 번호를 현재 배포 버전으로 간주하지 않습니다.
