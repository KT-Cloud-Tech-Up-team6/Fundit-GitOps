# Payment 배포 전제조건

`fundit-payment`는 CNPG의 `app` 데이터베이스를 사용합니다.
Flyway V1이 `payment`, `refund`, `settlement` 스키마를 만들고, Flyway 이력은 `public` 스키마에 기록합니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `dev/fundit-payment-secret`
  - `payment-encryption-key`: Base64 AES-256 32바이트 키
  - `toss-widget-secret-key`: dev Toss Widget Secret
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka
- `fundit-order-svc`: 펀딩 내부 조회 대상
- `fundit-fulfillment-svc`: 배송 상태 내부 조회 대상

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.
`payment-encryption-key`는 암호화 데이터가 쌓인 뒤 변경하면 기존 데이터를 복호화할 수 없으므로 최초 설정 후 고정합니다.

## 내부 서비스 연동

dev에서는 Order와 Fulfillment 클라이언트를 실제 HTTP 모드로 사용합니다.

- `ORDER_FUNDING_CLIENT_MODE=http`
- `SHIPPING_STATUS_CLIENT_MODE=http`

Payment, Order, Fulfillment가 동일한 `internal-api-key`를 사용해야 합니다.

## S3 IRSA

환불 증빙 Presigned URL 기능은 `fundit-backend-sa`를 사용합니다.
Infra #80 / PR #105에서 `FunditBackendS3Role-fundit-dev-eks`가 생성된 뒤 배포해야 합니다.
현재 이 ServiceAccount를 참조하는 Deployment는 Payment뿐입니다.

## Gateway 경로

Gateway의 `PAYMENT_SERVICE_BASE_URL`은 이미 `http://fundit-payment-svc:8080`으로 설정되어 있습니다.
Payment 배포 후 `/api/v1/payments/**`, `/api/v1/refunds/**`, `/api/v1/settlements/**`와 v2 Payment·Refund 경로가 연결됩니다.

## 배포 이미지

Backend `develop`의 성공한 payment-service CI/CD 결과를 tag와 digest로 고정합니다.

- commit: `7dd5bd525f5080548f4e2fd7fee835a7fa0e92a9`
- image digest: `sha256:e7a821e63fb4bbe148b541e5ce23507d426f4c19ec0ab732b24b98d13abcad33`
