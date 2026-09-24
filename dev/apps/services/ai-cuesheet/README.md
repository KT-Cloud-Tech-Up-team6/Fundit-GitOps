# Cuesheet AI dev 배포 초안

이 이미지는 내부 API `POST /cue-sheets`를 8420 포트에서 제공합니다. 외부 Ingress는 만들지 않습니다.
이미지는 ECR의 성공한 push 결과를 tag와 digest로 고정합니다.

## 병합 전 준비

`dev/fundit-ai-cuesheet-secret`에 아래 키를 안전한 비밀 관리 경로로 등록해야 합니다.

- `cuesheet-ai-token`: AI의 `CUESHEET_AI_TOKEN`이며 향후 Live의 `LIVE_CUESHEET_AI_TOKEN`과 같은 값
- `vertexai-key`: 현재 이미지가 Gemini Vertex express mode에 사용하는 `vertexaiKEY`

두 값 중 하나라도 비어 있으면 컨테이너가 기동을 중단합니다. Secret 원문은 Git, PR, 로그에 기록하지 않습니다.
`model_no1=gemini-2.5-flash`는 현재 코드의 기본값을 명시한 초안이며, AI팀이 선택한 dev 모델과 접근 권한을 병합 전에 확인해야 합니다.

이미지의 BE 연동 API는 생성 결과를 동기 응답으로 돌려주고 `/app/projects`의 생성 파일은 휘발성으로 취급합니다.
따라서 해당 경로에 크기 제한이 있는 `emptyDir`를 연결했습니다. Pod 재시작 시 파일은 사라지며,
장기 보존이 필요한지와 요청 파일 정리 정책은 AI팀과 확인해야 합니다.

배포 후에는 `/docs` 헬스체크, Bearer 토큰 누락 시 401, 인증된 `POST /cue-sheets`,
Gemini 실제 호출을 각각 검증합니다. `/docs` 응답만으로 모델 호출 성공을 판단하지 않습니다.
Live의 `LIVE_AI_MODE` 전환은 Copilot과 Cuesheet 양쪽이 준비된 뒤 별도 PR에서 진행합니다.
