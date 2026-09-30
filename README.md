# Fundit-GitOps

Fundit의 Kubernetes 배포 상태를 선언하고 Argo CD로 EKS에 반영하는 저장소입니다.
AWS 네트워크, EKS 클러스터와 컨트롤러 설치는 `Fundit-Infra`가 관리하고, 이 저장소는
애플리케이션 워크로드와 클러스터 운영 정책을 관리합니다.

## 배포 흐름

```text
Application Repository
  → Build / Test
  → Docker Image Build
  → Amazon ECR Push
  → Fundit-GitOps의 이미지 참조 변경
  → Argo CD 자동 동기화
  → EKS 배포
```

GitHub Actions가 EKS에 직접 배포하지 않습니다. `main`에 반영된 선언을 Argo CD가 감지해
자동으로 동기화하며, 제거된 리소스는 prune하고 수동 변경은 self-heal합니다.

## 저장소 구조

```text
Fundit-GitOps/
├── root.yaml                    # App of Apps 진입점 (apps/ 재귀 탐색)
├── apps/
│   ├── dev.yaml                 # dev/ Kustomize 진입점
│   ├── prod.yaml                # prod/** 재귀 동기화
│   └── projects/                # 환경별 Argo CD AppProject
├── dev/
│   ├── kustomization.yaml       # dev 리소스 등록의 최상위 목록
│   ├── apps/                    # Frontend·Gateway·Ingress·Backend·AI 서비스
│   ├── cnpg/                    # PostgreSQL Cluster·백업 정책
│   ├── external-secrets/        # SecretStore·ExternalSecret
│   ├── karpenter/               # NodePool·EC2NodeClass
│   ├── monitoring/              # PrometheusRule 등 관제 정책
│   ├── storage/                 # StorageClass
│   ├── hpa/                     # HPA 준비 영역 (현재 미등록)
│   └── keda/                    # ScaledObject 준비 영역 (현재 미등록)
├── staging/                     # staging 정책 준비 영역
└── prod/                        # prod 정책 준비 영역
```

`root.yaml`은 `apps/`를 재귀 탐색하지만, `apps/dev.yaml`은 `dev/`의
`kustomization.yaml`을 Kustomize 진입점으로 사용합니다. 새 dev 리소스는 파일을 배치하는
것만으로 배포되지 않습니다. 상위 `kustomization.yaml`의 `resources`에도 등록해야 합니다.
`prod/`는 아직 디렉터리 재귀 탐색 방식이며 `staging/`에는 Application이 없습니다.

## Argo CD Bootstrap

Fundit-Infra의 `terraform-cd.yml`은 Argo CD 레이어를 적용할 때 컨트롤러 기동을 기다린 뒤
`root.yaml`을 적용하고 `fundit-root` 동기화를 확인합니다. 자동화가 실행되지 않은 초기 설치나
복구 시에만 클러스터 관리자가 컨텍스트를 확인한 뒤 수동 적용합니다.

```bash
kubectl config current-context
kubectl apply -f root.yaml
```

이후 `fundit-root`가 `apps/**`를 관리하고, `fundit-dev`와 `fundit-prod`가 환경별 리소스를
관리합니다.

## 환경 상태

| 환경 | 상태 | Argo CD 경로 |
| --- | --- | --- |
| `dev` | 사용 중 | `dev/` |
| `staging` | 준비 영역 | `staging/` |
| `prod` | Application 골격만 존재 | `prod/` |

현재 dev에는 Frontend·Gateway·Ingress, Backend MSA, AI Cuesheet, CNPG PostgreSQL,
ExternalSecret, Karpenter, gp3 StorageClass 및 모니터링 정책이 등록되어 있습니다.
HPA·KEDA 리소스는 아직 최상위 Kustomization에 등록되지 않았습니다.

## 매니페스트 작성 규칙

- dev 리소스는 명시적으로 `namespace: dev` 또는 해당 운영 네임스페이스를 지정합니다.
- Deployment에는 CPU·메모리 `requests`/`limits`와 Startup·Readiness·Liveness Probe를 둡니다.
- 이미지에는 `latest`를 쓰지 않고 커밋 SHA 태그 또는 digest를 사용합니다.
- Service의 selector와 Pod label, Service port 이름을 정확히 맞춥니다.
- 민감하지 않은 런타임 값은 ConfigMap, 비밀번호·API Key는 Secret 참조로 전달합니다.
- Secret 값, 토큰, 인증서 원문은 Git에 저장하지 않습니다.
- 인터넷 트래픽은 ALB Ingress에서 Frontend와 Gateway로만 전달하고, 내부 MSA는 ClusterIP로 둡니다.
- 클러스터 범위 리소스는 환경별 AppProject의 `clusterResourceWhitelist` 허용 여부를 확인합니다.
- 새 서비스 디렉터리에는 `kustomization.yaml`을 두고, 상위 Kustomization의 `resources`에 연결합니다.
- 서비스 이미지 tag와 digest는 해당 서비스의 `kustomization.yaml`에서 함께 관리합니다.

권장 공통 label:

```yaml
metadata:
  labels:
    app.kubernetes.io/name: <component>
    app.kubernetes.io/part-of: fundit
```

## 이미지 계약

| 구분 | ECR Repository | 태그 형식 |
| --- | --- | --- |
| Backend MSA | `fundit-backend` | `sha-<service-name>-<git-commit-sha>` |
| Frontend | `fundit-frontend` | `sha-<git-commit-sha>` |
| AI Cuesheet | `fundit-ai-cuesheet` | `sha-<git-commit-sha>` |
| AI Copilot·Highlight | 서비스별 ECR Repository | `sha-<git-commit-sha>` |

태그는 소스 커밋 추적에 사용하고, Deployment에는 가능하면 `tag@sha256:digest` 형식으로
digest까지 고정합니다. 롤백할 수 있도록 배포에 사용한 digest를 Git 이력에 남깁니다.

### 자동 이미지 갱신

Frontend CI는 ECR push 후 `cd-dispatch-frontend-image.yml`을 호출합니다. Backend와
Copilot·Highlight용 진입점은 각각 `cd-dispatch-backend-image.yml`,
`cd-dispatch-copilot-image.yml`, `cd-dispatch-highlight-image.yml`입니다. 이 세
진입점은 GitOps 쪽 허용 목록에서 ECR Repository와 수정 파일을 고정하며, tag/SHA,
ECR tag→digest, 소스 브랜치 및 Backend 서비스별 전진 여부를 검증합니다. 이미지
값 외의 파일 변경이 생기면 push하지 않습니다.

BE·AI 자동 배포는 각 소스 저장소의 ECR push 성공 후 dispatch 단계와 Actions Secret
`FUNDIT_GITOPS_TOKEN`, 그리고 GitOps의 `GITOPS_BE_AI_ECR_READ_ROLE_ARN`에 지정된
ECR 읽기 Role이 준비된 뒤에만 동작합니다. 소스 CI에는 GitOps `Actions: write`만
부여하고 `Contents: write`는 부여하지 않습니다. 외부 호출이 실패하면 GitOps
Actions 실행 기록에서 입력 검증·ECR 검증·push 단계를 확인한 뒤, 원인 수정 후
같은 tag/digest로 다시 호출합니다. 잘못된 이미지가 반영되면 마지막 정상 digest의
Git commit으로 revert한 뒤 Argo CD Sync와 Pod imageID를 확인합니다.

AI Cuesheet는 비공개 소스 브랜치 검증 권한이 정해지지 않아, Funding Story는
Flyway migration 이미지의 선행 성공을 보장하는 전용 흐름이 필요해 이번
단순 이미지 갱신 진입점에서 제외합니다.

## 변경 및 검증

1. 이슈를 만들고 작업 범위를 합의합니다.
2. 관련 이슈 번호와 작업 목적을 식별할 수 있는 브랜치를 만듭니다.
3. 로컬에서 공백 오류와 Kubernetes API 검증을 수행합니다.
4. PR에서 Argo CD 영향 범위, Secret 포함 여부와 파괴적 변경을 확인합니다.
5. 병합 후 Argo CD Sync·Health와 실제 Pod·Service 상태를 확인합니다.

검증 예시:

```bash
git diff --check
kubectl kustomize dev >/dev/null
kubectl apply --dry-run=server -k dev
```

`dry-run=server`는 대상 클러스터의 CRD와 Admission 정책을 사용하므로 클러스터 접근 권한이
필요합니다. 실제 적용 명령은 Argo CD가 수행합니다.

## 롤백

애플리케이션 장애 시 마지막 정상 이미지 digest가 기록된 Git revision으로 되돌립니다.
Argo CD가 되돌린 선언을 자동 동기화한 뒤 Deployment rollout과 Health Check를 확인합니다.
DB·PVC·StorageClass처럼 데이터에 영향을 주는 리소스는 단순 revert 전에 영향도를 검토합니다.

## 관련 저장소

- `Fundit-Infra`: AWS·EKS 및 클러스터 애드온 설치
- `Fundit-backend`: Spring Boot MSA 이미지 빌드·ECR Push
- `Fundit-FE`: Next.js 이미지 빌드·ECR Push

EC2 Docker Compose·SSM 배포 코드는 EKS·Argo CD 전환에 따라 Issue #28에서 제거했습니다.
