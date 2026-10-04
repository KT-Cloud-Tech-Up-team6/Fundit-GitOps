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

Backend `develop`의 성공한 notification-service 이미지가 GitOps 자동 갱신으로 반영됩니다.
현재 선언된 tag와 digest는 이 디렉터리의 `kustomization.yaml` `images` 항목에서 확인합니다.
실제 배포 이미지는 `dev/fundit-notification` Deployment와 Pod의 `imageID`로 대조합니다.
이전 CI 커밋이나 실행 번호를 현재 배포 버전으로 간주하지 않습니다.
