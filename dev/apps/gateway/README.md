# Gateway 배포 전제조건

`fundit-gateway`는 다음 리소스가 준비된 뒤 정상 기동합니다.

- `fundit-backend-secrets` Secret의 `internal-api-key` 키
- `fundit-auth-svc`, `fundit-member-svc`, `fundit-payment-svc`
- `fundit-fulfillment-svc`, `fundit-order-svc`, `fundit-project-svc`, `fundit-search-svc`
- `fundit-notification-svc`, `fundit-live-svc`

Secret 값은 Git에 저장하지 않습니다. ConfigMap의 Service 이름은 각 백엔드 서비스
매니페스트에서도 동일하게 사용해야 합니다.

Live 및 Notification 라우팅을 포함한 Gateway 이미지를 tag와 digest로 고정합니다.

- commit: `ae1e0320e466e18e380cf76d7e9fd8c292a35cd6`
- CD run: `35577491723`
