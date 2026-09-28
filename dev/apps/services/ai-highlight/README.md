# Highlight AI dev 내부 기동 초안

성공한 AI 이미지 push 결과를 tag와 digest로 고정했습니다. `fundit-ai-highlight-svc.dev.svc.cluster.local:8000`의 ClusterIP만 만듭니다. 외부 Ingress, Live 콜백, 영상 처리 작업은 이 단계에 포함하지 않습니다.

## 병합 전 필수 조건

- `dev/fundit-ai-highlight-secret`에 `gemini-api-key`를 안전한 비밀 관리 경로로 등록해야 합니다. 이 값은 AI팀에서 받아야 하며 Git, PR, 로그에 기록하지 않습니다. Secret이 없거나 값이 비어 있으면 Pod는 기동하지 않습니다.
- 현재 dev 노드에는 GPU가 없습니다. `/api/v1/ai/health`의 `ok`는 기본 구성 확인이며 GPU 성능이나 실제 영상 처리 성공을 뜻하지 않습니다. 이 PR은 내부 헬스체크까지만 검증합니다.

## 배포 후 확인

`kubectl -n dev rollout status deployment/fundit-ai-highlight`와 Pod Ready 상태를 확인합니다. 포트 포워딩 또는 클러스터 내부에서 `/api/v1/ai/health`를 조회하고 HTTP 200뿐 아니라 JSON의 `ok: true`, `ffmpeg: true`, `whisper: true`, `gemini_key: true`를 확인합니다. 실제 Gemini 호출은 별도 검증해야 합니다.

## 정식 연동 전 결정 사항

- `/data`는 현재 1Gi `emptyDir`라 Pod 교체 시 영상·모델 캐시·결과물이 사라집니다. 처리 규모에 맞는 PVC, 보존·정리 정책과 GPU 노드 용량을 협의해야 합니다.
- 현재 AI API의 파일 조회 경로에는 인증이 없고 다른 AI 서비스와 `/api/v1/ai` 경로가 겹칩니다. 인증·독립 라우팅이 정해지기 전 외부 공개를 금지합니다.
- 이미지 기본 `PUBLIC_BASE_URL`은 localhost이므로 그대로 작업을 실행하면 브라우저가 재생할 수 없는 URL이 Live에 저장될 수 있습니다. 공개 URL과 접근 정책 확정 후에만 이를 설정합니다.
- `LIVE_SERVICE_URL`과 `INTERNAL_API_KEY`는 이번 초안에서 주입하지 않습니다. AI→Live 콜백 주소·키와 영상 URL이 함께 확정된 뒤 별도 변경으로 연동합니다.
