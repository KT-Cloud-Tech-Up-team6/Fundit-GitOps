# Copilot AI dev 배포 전제조건

이미지는 `fundit-ai-copilot` ECR의 검증 대상 태그와 digest로 고정합니다.
외부 Ingress는 만들지 않으며, 향후 Backend Live가 내부 Service의 `/api/v1/ai` 경로를 호출합니다.
이번 PR은 Live의 `LIVE_AI_MODE`를 변경하지 않습니다. Live 실연동에는 별도 Cuesheet AI 주소·토큰까지 준비한 뒤 5개 환경변수를 동시에 반영해야 합니다.

병합 전에 `dev` namespace에 다음 두 Kubernetes Secret을 안전한 비밀 관리 경로로 준비해야 합니다.

- `fundit-ai-copilot-gcp-sa`의 `service-account.json`: Copilot 전용 GCP Service Account JSON입니다. Vertex AI ADC 인증에 사용하며, 컨테이너에 read-only로 mount합니다.
- `fundit-ai-copilot-secret`의 `api-token`: Copilot의 `API_TOKEN`입니다. Live 연동을 켤 때 Backend의 `LIVE_AI_TOKEN`과 동일한 값으로 사용합니다.

Secret 원문은 Git, PR, 로그에 기록하지 않습니다. `GEMINI_API_KEY`는 사용하지 않습니다.
컨테이너는 JSON을 `/var/secrets/google/service-account.json`으로 mount하고, `GOOGLE_APPLICATION_CREDENTIALS`가 그 경로를 가리킵니다.
시작 시 `API_TOKEN`과 JSON 파일 존재를 확인하며, 하나라도 없으면 기동을 중단합니다.

`/data`는 `gp3-retain` PVC에 연결하고 `LIVE_KNOWLEDGE_PATH`와 `RUNTIME_DIR`을 그 아래로 지정합니다.
EBS `ReadWriteOnce` 볼륨을 단일 Pod에서 사용하므로 업데이트 전략은 `Recreate`입니다. Pod 재시작 후 `/data/live_knowledge.json`의 답변 보존을 실제로 확인합니다.
단, 프로세스 메모리의 방송 상태 전체가 PVC에서 복원되는 것은 아닙니다.

배포 후에는 `/api/v1/ai/health`, 인증된 Copilot 호출, Vertex AI 실제 호출을 각각 검증합니다.
Health 응답만으로 Google ADC 또는 모델 사용 가능 여부를 판단하지 않습니다.
