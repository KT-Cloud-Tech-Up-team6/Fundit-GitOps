# Auth 배포 전제조건

`fundit-auth`는 CNPG의 `app` 데이터베이스 안에서 `auth` 스키마를 사용합니다.
Flyway가 스키마와 이력 테이블을 생성하며 Member의 migration과 분리됩니다.

배포 전에 `dev/fundit-auth-secret`에 다음 키가 있어야 합니다.

- `jwt-private-key`: PKCS#8 DER를 Base64로 인코딩한 한 줄 RSA 개인키
- `auth-encryption-key`: 32바이트 AES 키의 Base64 값
- `pg-store-id`, `pg-api-key`
- `kakao-client-id`, `kakao-client-secret`, `kakao-redirect-uri`
- `google-client-id`, `google-client-secret`, `google-redirect-uri`

공유 `dev/fundit-backend-secrets`에는 `internal-api-key` 키가 필요합니다.
실제 값은 Git과 이 문서에 기록하지 않습니다.
