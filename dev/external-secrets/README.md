# External Secrets

dev 애플리케이션 Secret을 AWS Secrets Manager와 Parameter Store에서 생성합니다.
External Secrets Operator와 IRSA Role은 Fundit-Infra `terraform/envs/dev/15-external-secrets`에서 설치합니다.

## 저장 위치

| Kubernetes Secret | Secrets Manager | Parameter Store |
|---|---|---|
| `fundit-auth-secret` | `fundit/dev/auth` | `/fundit/dev/auth/{google-client-id,google-redirect-uri,kakao-client-id,kakao-redirect-uri,pg-store-id}` |
| `fundit-member-secret` | `fundit/dev/member` | |
| `fundit-payment-secret` | `fundit/dev/payment` | |
| `fundit-backend-secrets` | `fundit/dev/backend` | |

비밀번호·API 키·토큰·암호화 키는 Secrets Manager에 둡니다.
client-id·redirect-uri·store-id 같은 설정값은 Parameter Store에 둡니다.
ESO Role은 `fundit/dev/*` 아래만 읽을 수 있습니다.

## 값 변경

AWS 콘솔이나 CLI에서 값을 바꿉니다.
ExternalSecret의 `refreshInterval`이 1시간이라 최대 1시간 뒤 Kubernetes Secret에 반영됩니다.
환경변수로 읽는 서비스는 파드를 재시작해야 새 값을 씁니다.

## 주의

`creationPolicy: Owner`라서 ExternalSecret을 지우면 Kubernetes Secret도 함께 지워집니다.
ExternalSecret 파일(`auth.yaml` `member.yaml` `payment.yaml` `backend.yaml`)을 삭제하면 Argo CD prune으로 해당 Secret도 지워지고 이후 재시작하는 파드는 기동에 실패합니다.
키는 `data[].remoteRef`로 하나씩 지정합니다. `dataFrom.find`는 ESO Role에 권한이 없어 동작하지 않습니다.
