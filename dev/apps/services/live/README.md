# Live 배포 전제조건

`fundit-live`는 CNPG의 `app` 데이터베이스 안에서 `live` 스키마를 사용합니다.
Flyway가 스키마와 이력 테이블을 생성하며 다른 서비스의 migration과 분리됩니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.

## IVS 및 Kafka

- Live 서비스의 AWS IVS 및 IVS Chat API 호출을 위해 IRSA 전용 ServiceAccount(`fundit-live-sa`, Role: `FunditLiveIvsRole-fundit-dev-eks`)가 연결되어 있습니다.
- 환경설정에 따라 `LIVE_IVS_MODE`를 실제 AWS IVS 연동 모드로 전환할 수 있습니다.
- 현재 이미지의 Live 서비스는 Kafka 이벤트를 발행만 하며 구독 토픽과 Redis 설정을 요구하지 않습니다.

## Gateway 경로

Gateway의 `LIVE_SERVICE_BASE_URL`은 `http://fundit-live-svc:8080`을 사용합니다.
외부 `/api/v1/lives/**` 요청은 Live 서비스로 전달되며 `/internal/v1/lives/**`는 노출하지 않습니다.

## 배포 이미지

Backend `develop`의 성공한 live-service CI/CD 결과를 tag와 digest로 고정합니다.

- commit: `11c61dedb7fe6248d41ab1f00979b80577590301`
- CD run: `35696732130`
