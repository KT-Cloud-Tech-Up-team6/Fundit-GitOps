# Fulfillment 배포 전제조건

`fundit-fulfillment`는 CNPG의 `app` 데이터베이스 안에서 `fulfillment` 스키마를 사용합니다.
Flyway가 스키마와 이력 테이블을 생성하며 다른 서비스의 migration과 분리됩니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka
- `fundit-order-svc`: 펀딩 내부 조회 대상
- `fundit-project-svc`: 프로젝트 소유권 내부 조회 대상

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.

## 내부 서비스 연동

dev에서는 두 클라이언트를 실제 HTTP 모드로 사용합니다.

- `ORDER_FUNDING_CLIENT_MODE=http`
- `PROJECT_OWNERSHIP_CLIENT_MODE=http`

Order와 Project가 동일한 `internal-api-key`를 사용해야 하며, 값이 다르면 내부 호출이 401로 실패합니다.

## Kafka

Fulfillment 서비스는 `funding.succeeded.v1`을 `fulfillment-service` consumer group으로 소비합니다.
배송 완료 등 후속 도메인 이벤트는 transactional outbox를 통해 발행합니다.

## Gateway 경로

Gateway의 `FULFILLMENT_SERVICE_BASE_URL`은 `http://fundit-fulfillment-svc:8080`을 사용합니다.
Project 하위 Fulfillment·Shipment의 v1/v2 경로가 Fulfillment 서비스로 전달됩니다.

## 배포 이미지

Backend `develop`의 성공한 fulfillment-service CI/CD 결과를 tag와 digest로 고정합니다.

- commit: `9b8db1bf55bf8da762ad2f62f6c63706ecedbfc3`
- CD run: `35573703082`
