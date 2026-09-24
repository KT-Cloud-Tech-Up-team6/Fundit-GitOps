# Live 배포 전제조건

`fundit-live`는 CNPG의 `app` 데이터베이스 안에서 `live` 스키마를 사용합니다.
Flyway가 스키마와 이력 테이블을 생성하며 다른 서비스의 migration과 분리됩니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `dev/fundit-ai-copilot-secret`: `api-token` 키 (Copilot의 `API_TOKEN`과 동일한 값)
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.

## Copilot AI

`LIVE_AI_MODE=http`으로 Copilot 내부 Service(`http://fundit-ai-copilot-svc:8080/api/v1/ai`)를 호출합니다.
Copilot Secret과 Pod가 준비되기 전에는 이 변경을 main에 병합하지 마세요.
인증된 실제 요청으로 AI 연동을 확인해야 하며, Copilot의 `/health` 응답만으로 Gemini 호출 성공을 판단하지 않습니다.

## IVS 및 Kafka

현재 dev 배포는 `LIVE_IVS_MODE=stub`을 사용하므로 AWS IVS 자격증명이 필요하지 않습니다.
실제 IVS 연동은 AWS 담당자와 IAM 권한 및 선택 설정을 별도로 확정한 뒤 진행합니다.

현재 이미지의 Live 서비스는 Kafka 이벤트를 발행만 하며 구독 토픽과 Redis 설정을 요구하지 않습니다.

## Gateway 경로

Gateway의 `LIVE_SERVICE_BASE_URL`은 `http://fundit-live-svc:8080`을 사용합니다.
외부 `/api/v1/lives/**` 요청은 Live 서비스로 전달되며 `/internal/v1/lives/**`는 노출하지 않습니다.

## 배포 이미지

Backend `develop`의 성공한 live-service CI/CD 결과를 tag와 digest로 고정합니다.

- commit: `11c61dedb7fe6248d41ab1f00979b80577590301`
- CD run: `35696732130`
