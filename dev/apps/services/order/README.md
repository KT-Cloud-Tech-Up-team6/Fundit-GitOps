# Order 배포 전제조건

`fundit-order`는 CNPG의 `app` 데이터베이스 안에서 `order_service` 스키마를 사용합니다.
SQL 예약어 `order`와의 충돌을 피하기 위해 스키마 이름을 `order_service`로 지정합니다.
Flyway가 스키마와 이력 테이블을 생성하며 다른 서비스의 migration과 분리됩니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka
- `fundit-project-svc`: 프로젝트·리워드 내부 조회 대상
- `fundit-fulfillment-svc`: 주문 상세의 배송 상태 조회 대상

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.
Fulfillment 배포 전에도 Order는 기동할 수 있지만 배송 상태가 필요한 기능은 정상 동작하지 않습니다.

## Kafka

Order 서비스는 회원가입, 리워드, 결제·환불, 펀딩 마감 이벤트를 소비하고 펀딩 상태와 알림·통계 이벤트를 발행합니다.
최초 배포 시 `order-service` consumer group의 partition 할당과 과거 이벤트 처리 오류를 확인합니다.

## 일회성 백필

`ORDER_BACKFILL_FUNDING_PROJECT_PUBLIC_ID`는 안전을 위해 `false`로 고정합니다.
백필이 필요할 때는 Backend 팀과 대상 데이터 및 실행 절차를 별도로 합의한 뒤 일시적으로 사용합니다.

## Gateway 경로

Gateway의 `ORDER_SERVICE_BASE_URL`은 `http://fundit-order-svc:8080`을 사용합니다.
Order, Coupon, Restock Notification 및 Project 하위 주문·후원자 경로가 Order 서비스로 전달됩니다.

## 배포 이미지

Backend `develop`의 성공한 order-service CI/CD 결과를 tag와 digest로 고정합니다.

- commit: `ce52dd63dac932cb14393bfc1567862d13605934`
- CD run: `35709719859`
