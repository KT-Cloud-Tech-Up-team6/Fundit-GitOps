# Project 배포 전제조건

`fundit-project`는 CNPG의 `app` 데이터베이스 안에서 `project` 스키마를 사용합니다.
Flyway가 스키마와 이력 테이블을 생성하며 다른 서비스의 migration과 분리됩니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka
- `fundit-media-dev-team6`: Project 미디어 업로드용 S3 버킷
- `fundit-order-svc`: 재고 조회 연동 대상. Order 배포 전에는 해당 기능이 동작하지 않습니다.

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.

## S3 권한

Project의 미디어 업로드 URL 발급과 객체 확인에는 S3 접근 권한이 필요합니다.
자격증명을 환경변수나 Secret으로 직접 주입하지 않고 AWS SDK 기본 자격증명 체계를 사용합니다.
S3 권한은 IRSA로 받습니다.
Deployment는 `fundit-backend-sa`를 사용합니다.
이 ServiceAccount는 `FunditBackendS3Role-fundit-dev-eks`와 연결됩니다.
`fundit-backend-sa`는 `dev/apps/services/payment/serviceaccount.yaml`에 정의되어 있습니다.

## Gateway 경로

Gateway의 `PROJECT_SERVICE_BASE_URL`은 `http://fundit-project-svc:8080`을 사용합니다.
Project 관련 `/api/v1/*` 경로 정의는 Gateway 애플리케이션에 포함되어 있습니다.

## 배포 이미지

Backend `develop`의 성공한 project-service CI/CD 결과를 tag와 digest로 고정합니다.

- commit: `ce5d882817477852e9fdfa8a21e5cc3a060daaa6`
- CD run: `35677462680`
