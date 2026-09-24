# Copilot AI dev 배포 전제조건

이미지는 `fundit-ai-copilot` ECR의 검증 대상 태그와 digest로 고정합니다.
외부 Ingress는 만들지 않으며, 향후 Backend Live가 내부 Service의 `/api/v1/ai` 경로를 호출합니다.
이번 PR은 Live의 `LIVE_AI_MODE`를 변경하지 않습니다. Live 실연동에는 별도 Cuesheet AI 주소·토큰까지 준비한 뒤 5개 환경변수를 동시에 반영해야 합니다.

병합 전에 `dev/fundit-ai-copilot-secret`을 안전한 비밀 관리 경로로 준비해야 합니다.

- `gemini-api-key`: Copilot의 `GEMINI_API_KEY`
- `api-token`: Copilot의 `API_TOKEN`이자 Live Backend의 `LIVE_AI_TOKEN`

Secret 원문은 Git, PR, 로그에 기록하지 않습니다. `API_TOKEN`을 비워 두면 AI 서버 인증이 비활성화되므로 컨테이너 시작 시 두 필수 키의 비어 있음 여부를 검사하고, 비어 있으면 기동을 중단합니다.

`/data`는 `gp3-retain` PVC에 연결하고 `LIVE_KNOWLEDGE_PATH`와 `RUNTIME_DIR`을 그 아래로 지정합니다.
EBS `ReadWriteOnce` 볼륨을 단일 Pod에서 사용하므로 업데이트 전략은 `Recreate`입니다. Pod 재시작 후 `/data/live_knowledge.json`의 답변 보존을 실제로 확인합니다.
단, 프로세스 메모리의 방송 상태 전체가 PVC에서 복원되는 것은 아닙니다.

배포 후에는 `/api/v1/ai/health`, Live→Copilot Bearer 인증 호출, Gemini 실제 호출을 각각 검증합니다.
Health 응답만으로 API 키나 모델 사용 가능 여부를 판단하지 않습니다.
