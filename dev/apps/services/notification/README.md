# Notification 배포 전제조건

`fundit-notification`은 CNPG의 `app` 데이터베이스 안에서 `notification` 스키마를 사용합니다.
Flyway가 스키마와 이력 테이블을 생성하며 다른 서비스의 migration과 분리됩니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.

## Kafka

Notification 서비스는 다음 토픽을 소비합니다.

- `notification.raised.v1`
- `live.started.v1`

consumer group은 `notification-service`이며 `auto-offset-reset=earliest`입니다.
최초 배포 시 Kafka에 보존된 과거 이벤트가 처리될 수 있으므로 로그와 생성 건수를 확인합니다.

## Gateway 경로

Gateway의 `NOTIFICATION_SERVICE_BASE_URL`은 `http://fundit-notification-svc:8080`을 사용합니다.

- `/api/v1/notifications/**`
- `/api/v1/notification-settings/**`
- `/api/v1/lives/*/notify`

## 배포 이미지

Backend `develop`의 성공한 notification-service CI/CD 결과를 tag와 digest로 고정합니다.

- commit: `11c61dedb7fe6248d41ab1f00979b80577590301`
- CD run: `35696640498`
