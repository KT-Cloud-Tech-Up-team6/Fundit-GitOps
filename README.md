# Fundit-GitOps

개발 EC2에 배포할 이미지와 Docker Compose 실행 구성을 관리합니다. 현재 첫 대상은
Fundit-backend의 `platform/gateway-service`입니다.

목표 배포 흐름은 다음과 같습니다.

```text
App Repo: Build/Test → Docker 이미지 빌드 → ECR Push
    → 이 저장소의 compose/dev/images.env 변경
GitOps: 설정 검증 → 개발 EC2에서 deploy-dev.sh 실행 → Health Check
```

현재 구현은 **Compose 구성, 서버 실행 스크립트, 설정 검증 CI, SSM 수동 배포 workflow**까지입니다.
배포 workflow는 `main`의 `workflow_dispatch`만 받고, `DEV_DEPLOY_ENABLED=true`와
`dev-deploy` Environment 설정이 모두 갖춰진 뒤에만 실행됩니다. App Repo 이미지 빌드/ECR Push와
저장소 간 이미지 주소 갱신은 후속 작업입니다. 현재 CI 성공은 실제 배포 성공을 의미하지 않습니다.

## 담당 범위와 디렉터리

| 담당 | 범위 |
| --- | --- |
| 조용빈 — Docker / CI/CD | 이미지·태그 계약, Compose 구성, 검증 CI, 개발 서버 배포 자동화 |
| 이성규 — AWS 인프라 / 개발 서버 | EC2, Docker 실행 환경, ECR, IAM, 네트워크, 서버 초기 설정 |

```text
compose/dev/compose.yaml          Gateway 실행 정의
compose/dev/images.env            Git으로 관리하는 배포 이미지 주소
compose/dev/runtime.env.example   서버 런타임 설정의 빈 예제
scripts/deploy-dev.sh             서버에서 실행하는 배포·검증 스크립트
scripts/deploy-dev-revision.sh    고정 GitOps revision을 배포하는 서버 launcher 원본
scripts/dispatch-dev-deploy.py    SSM 대상·이미지·실행 결과 검증
.github/workflows/validate-dev-compose.yml
.github/workflows/deploy-dev-ssm.yml
tests/test_dispatch_dev_deploy.py SSM dispatcher 단위 테스트
```

EC2용 Compose는 `compose/dev/`에 둡니다. [PR #11](https://github.com/KT-Cloud-Tech-Up-team6/Fundit-GitOps/pull/11)의
Argo CD Application은 `dev/`를 재귀적으로 읽으므로 그 경로에 Compose YAML을 넣지 않습니다.
향후 EKS/Argo CD 전환 시 Kubernetes 매니페스트는 해당 구조에서 관리합니다.

## 이미지 계약

`compose/dev/images.env`에는 주석과 **따옴표 없는 `GATEWAY_IMAGE=...` 한 줄**만 둡니다.
현재 값은 배포를 차단하는 명시적 placeholder입니다. 실제 Gateway 이미지가 ECR에
올라온 후 주소를 바꿉니다. 아래 꺾쇠 부분은 모두 실제 배포 메타데이터로 대체해야 합니다.

```dotenv
GATEWAY_IMAGE=<AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/<ECR_REPOSITORY>:gateway-sha-<BACKEND_COMMIT_40_HEX>
```

- 지원 형식: `sha-<40자리 소문자 hex>`, `gateway-sha-<40자리 소문자 hex>` 등
  서비스 접두사가 붙은 SHA 태그 또는 `@sha256:<64자리 소문자 hex>` digest.
- SHA는 이미지를 만든 **백엔드 소스 커밋**입니다. GitOps 커밋 SHA가 아닙니다.
- digest 사용을 권장합니다. SHA 이름만으로 ECR 태그 덮어쓰기가 차단되지는 않으므로
  태그를 쓸 경우 ECR 불변 태그 정책 또는 팀의 재사용 금지 규칙을 함께 정해야 합니다.
- ECR 저장소 이름은 인프라 담당자와 확정합니다. `fundit-backend`를 여러 서비스가
  공유한다면 `gateway-sha-...`처럼 서비스명을 포함해야 같은 소스 커밋 간 충돌을 막습니다.
- 스크립트는 Git의 이미지를 읽으며, 호출 셸에 남아 있는 `GATEWAY_IMAGE` 값은 무시합니다.
- Compose에는 `build:`가 없습니다. 이 서버에서 Java 소스를 빌드하지 않습니다.
- 이미지는 실행 가능한 Gateway, Java 25 런타임, EC2와 맞는 CPU 아키텍처를 포함해야 합니다.
  현재 Infra의 AMI 설계는 `linux/amd64`이며 실제 서버와 대조해야 합니다.

## 서버 실행 환경

| 항목 | 필요한 설정 |
| --- | --- |
| OS | Linux. Infra에서 계획한 Ubuntu 22.04 amd64 기준 |
| Docker | 실행 중인 Docker Engine, 배포 사용자의 Docker 접근 권한 |
| Compose | **2.30.0 이상**의 시스템 설치 plugin (`docker compose`) |
| 기타 도구 | Bash 4.4 이상, AWS CLI v2, curl, flock, 기본 coreutils/grep |
| AWS 인증 | EC2 역할 등 AWS 기본 credential chain을 통한 해당 ECR 이미지 Pull 권한 |
| 네트워크 | ECR/이미지 레이어 다운로드, Gateway의 downstream 서비스 접근 |
| 런타임 파일 | 예: `/etc/fundit/dev/gateway.env`, 배포 사용자가 읽을 수 있는 `600` 권한 |
| 배포 잠금 경로 | 예: `/var/lib/fundit/deploy/`, 배포 사용자 소유의 쓰기 가능한 디렉터리 |

Compose의 [`env_file.format: raw`](https://docs.docker.com/reference/compose-file/services/#format)는
2.30.0부터 지원됩니다. 키에 `$`가 포함돼도 환경변수 치환 없이 전달하기 위해 사용합니다.
Docker Engine의 정확한 설치 버전은 이성규 님과 서버 구성 단계에서 고정합니다.
이미지를 실행하는 서버에는 별도의 JDK/Gradle 설치가 필요하지 않습니다.

ECR Pull 권한에는 `ecr:GetAuthorizationToken`과 대상 저장소의
`ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchCheckLayerAvailability`가 필요합니다.
Terraform 관리자 Role의 존재가 앱 배포용 권한이 준비됐다는 의미는 아닙니다.
이 스크립트는 AWS 리소스나 IAM Role을 생성하지 않습니다.

Docker는 시스템 plugin과 기본 로컬 daemon을 사용하는 구성을 전제로 합니다.
사용자별 Docker context/plugin 설정을 복사하지 않고, 배포 중 임시 Docker config를
사용한 뒤 지워 ECR 인증 정보를 상시 보관하지 않습니다. 원격 Docker daemon은 대상이 아닙니다.

## 런타임 설정

서버 담당자가 `runtime.env.example`을 **Git checkout 밖의 파일**로 준비하고
네 값을 모두 채웁니다. 값은 실행 환경의 설정 관리 절차로 전달하며 Git에 저장하지 않습니다.

| 변수 | 의미 |
| --- | --- |
| `AUTH_SERVICE_BASE_URL` | 컨테이너에서 접근 가능한 인증 서비스 HTTP(S) 주소 |
| `MEMBER_SERVICE_BASE_URL` | 컨테이너에서 접근 가능한 회원 서비스 HTTP(S) 주소 |
| `PAYMENT_SERVICE_BASE_URL` | 컨테이너에서 접근 가능한 결제 서비스 HTTP(S) 주소 |
| `INTERNAL_API_KEY` | Gateway와 downstream 서비스들이 공유하는 내부 API 키 |

`KEY=value` 형식, Unix 줄바꿈을 사용합니다. 따옴표·셸 확장·줄 끝 주석을 추가하지 않습니다.
스크립트는 env 파일을 `source`하지 않습니다. 빈 값, 중복 키, 알 수 없는 키,
잘못된 URL 형식, Git checkout 내부 파일, group/other 접근 권한이 있는 파일을 거부합니다.

`SPRING_PROFILES_ACTIVE=dev`와 컨테이너의 `SERVER_PORT=8080`은 Compose에서 고정합니다.
서비스 주소의 `localhost`는 EC2 호스트가 아닌 **Gateway 컨테이너 자신**을 가리킵니다.
이 Compose는 Gateway만 생성합니다. 다른 Compose 프로젝트의 `auth-service` 같은 이름은
공유 네트워크를 구성하지 않으면 자동으로 해석되지 않습니다. 실제 downstream 주소와
네트워크는 개발 서버 구성 담당자와 맞춰야 합니다.

실제 설정으로 `docker compose config`나 `env`, 컨테이너 전체 inspect를 로그에 출력하지
않습니다. 설정 검증에는 [`config --quiet`](https://docs.docker.com/reference/cli/docker/compose/config/)를
사용합니다. 배포 스크립트도 runtime 값, ECR 로그인 토큰, 응답 본문, 애플리케이션 로그를 출력하지 않습니다.

## 설정 검증과 배포

아래는 서버 준비 후 실행할 명령입니다. GitOps checkout의 루트에서 실행합니다.

```bash
# 설정 검증만 수행: daemon 접속, AWS 로그인, 이미지 pull, 컨테이너 변경 없음
bash scripts/deploy-dev.sh --check /etc/fundit/dev/gateway.env

# 개발 EC2에서 실제 배포 수행
bash scripts/deploy-dev.sh /etc/fundit/dev/gateway.env
```

환경변수로 바꿀 수 있는 서버 측 배포 설정은 다음과 같습니다. 이 값들은 위 네 개의
애플리케이션 런타임 파일에 넣지 않고 배포 명령을 실행하는 셸에 전달합니다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `GATEWAY_BIND_ADDRESS` | `127.0.0.1` | 호스트 루프백 바인딩. 외부 진입이 필요하면 네트워크 검토 후 `0.0.0.0` |
| `GATEWAY_HOST_PORT` | `8080` | 호스트 포트. 컨테이너 포트는 8080 고정 |
| `HEALTH_TIMEOUT_SECONDS` | `120` | 기동 후 health 대기 시간, 최대 600초 |
| `DEPLOY_LOCK_FILE` | `/var/lib/fundit/deploy/dev.lock` | 같은 서버의 모든 배포가 공유해야 하는 잠금 파일 |

초기 기본 설정은 호스트의 `127.0.0.1:8080`에서 확인합니다. 서버 외부에서 직접 접근할
계획이면 바인딩 주소와 보안그룹을 함께 정해야 합니다. 배포 스크립트는 어떤 바인딩에서든
호스트 루프백으로 Health Check를 수행하므로 지정 가능한 주소는 `127.0.0.1`, `0.0.0.0`입니다.

실제 배포 순서:

1. Git 이미지 주소, 서버 런타임 파일, Compose 설정을 검증합니다.
2. 서버 공통 잠금을 획득합니다. 이미 배포 중이면 실패로 종료합니다.
3. 이미지 주소의 리전을 사용해 ECR에 로그인하고 Gateway 이미지를 받습니다.
4. Pull 성공 후 `docker compose up -d --no-build --pull never --no-deps gateway`를 실행합니다.
5. 대상 컨테이너가 실행 중이고 `/actuator/health`가 HTTP 200을 반환하는지 제한 시간 내 확인합니다.
6. 종료 시 임시 Docker 인증 파일을 제거하고 잠금을 해제합니다.

Compose project name은 `fundit-dev`로 고정합니다. 기존 컨테이너를 먼저 `down`하지 않고,
다른 서비스나 볼륨을 삭제하지 않습니다. Gateway 하나를 교체하므로 짧은 서비스 중단이
생길 수 있습니다. `unless-stopped` 재시작 정책과 local 로그 회전(10 MB × 3)을 적용합니다.

Health Check는 Gateway 프로세스의 기본 상태를 확인합니다. 인증/JWKS 호출,
downstream 응답, 외부 진입 경로까지 정상임을 보장하지 않습니다. 실제 이미지와
서비스가 준비되면 별도의 API 통합 확인이 필요합니다. 이미지 안의 curl 설치를
가정하지 않으며, 호스트 curl로 배포 시점에 검사합니다. 지속적인 관제는 후속 구성입니다.

## 실패 시 복구

- 사전 검증·잠금·로그인·Pull 실패: 컨테이너 갱신 명령을 실행하지 않습니다.
- `up` 또는 health 실패: 스크립트가 nonzero로 종료합니다. 컨테이너가 이미 교체됐을 수
  있으므로 **실패 종료가 자동 원복을 의미하지 않습니다.**
- 복구: 마지막으로 성공한 배포의 이미지 주소로 `images.env`를 되돌리는 변경을 만들고,
  그 구성을 서버에 반영한 뒤 같은 스크립트를 다시 실행해 health를 확인합니다.
- Compose나 런타임 설정도 바뀌었다면 해당 설정의 복구를 함께 검토해야 합니다.
  ECR 보존 정책으로 이전 이미지가 삭제되면 이미지 원복도 불가능하므로, 성공한 배포의
  Git revision과 이미지 digest를 기록하고 필요한 이미지를 보존해야 합니다.
- 상태 확인 시 로그나 환경변수 전체를 CI에 자동 업로드하지 않습니다.

## 검증 CI와 후속 연결

`Validate dev Compose`는 관련 파일의 PR/main push 또는 수동 실행에서 동작합니다.
GitHub-hosted Ubuntu runner의 도구로 Bash 문법/ShellCheck, dummy 데이터 기반
Compose 검증, 초기 placeholder 배포 차단을 검사합니다. 실제 이미지 참조가 등록되면
그 참조도 파싱·검증합니다. 계정 접근, 이미지 존재 여부, 이미지 실행은 검증하지 않습니다.
워크플로의 권한은 `contents: read`이며 AWS/GitHub Secret을 요구하지 않습니다.

다음 작업은 이성규 님과 EC2 Instance Profile·SSM Agent·ECR Pull 권한·서버 디렉터리·
환경변수 공급 방식을 확정하는 것입니다. 이후 App Repo의 ECR Push 및 `images.env` 갱신을
연결합니다. 현재 파일을 main에 반영해도 `DEV_DEPLOY_ENABLED`가 설정되기 전에는 원격 배포가 시작되지 않습니다.
