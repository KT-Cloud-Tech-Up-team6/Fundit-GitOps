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
├── root.yaml                    # App of Apps 진입점
├── apps/
│   ├── dev.yaml                 # dev/** 재귀 동기화
│   ├── prod.yaml                # prod/** 재귀 동기화
│   └── projects/                # 환경별 Argo CD AppProject
├── dev/
│   ├── cnpg/                    # PostgreSQL Cluster·백업 정책
│   ├── karpenter/               # NodePool·EC2NodeClass
│   ├── monitoring/              # PrometheusRule 등 관제 정책
│   ├── storage/                 # StorageClass
│   ├── hpa/                     # 애플리케이션 HPA
│   └── keda/                    # 이벤트 기반 스케일 정책
├── staging/                     # staging 정책 준비 영역
└── prod/                        # prod 정책 준비 영역
```

`apps/dev.yaml`은 `dev/` 아래 YAML을 재귀적으로 읽습니다. dev 리소스는 별도의 Application을
추가하지 않고 담당 디렉터리에 배치합니다.

## Argo CD Bootstrap

Argo CD 설치 직후에는 `root.yaml`을 한 번 적용해 App of Apps를 시작해야 합니다.

```bash
kubectl apply -f root.yaml
```

이후 `fundit-root`가 `apps/**`를 관리하고, `fundit-dev`와 `fundit-prod`가 환경별 리소스를
관리합니다. Bootstrap 자동화가 적용되기 전까지 이 최초 적용은 클러스터 관리자 작업입니다.

## 환경 상태

| 환경 | 상태 | Argo CD 경로 |
| --- | --- | --- |
| `dev` | 사용 중 | `dev/` |
| `staging` | 준비 영역 | `staging/` |
| `prod` | Application 골격만 존재 | `prod/` |

현재 dev에는 Karpenter, gp3 StorageClass, CNPG PostgreSQL, 모니터링 정책이 선언되어 있습니다.
애플리케이션 Deployment·Service·Ingress·HPA·KEDA 정책은 각 기능 이슈와 PR로 추가합니다.

## 매니페스트 작성 규칙

- dev 리소스는 명시적으로 `namespace: dev` 또는 해당 운영 네임스페이스를 지정합니다.
- Deployment에는 CPU·메모리 `requests`/`limits`와 Startup·Readiness·Liveness Probe를 둡니다.
- 이미지에는 `latest`를 쓰지 않고 커밋 SHA 태그 또는 digest를 사용합니다.
- Service의 selector와 Pod label, Service port 이름을 정확히 맞춥니다.
- 민감하지 않은 런타임 값은 ConfigMap, 비밀번호·API Key는 Secret 참조로 전달합니다.
- Secret 값, 토큰, 인증서 원문은 Git에 저장하지 않습니다.
- 인터넷 트래픽은 ALB Ingress에서 Frontend와 Gateway로만 전달하고, 내부 MSA는 ClusterIP로 둡니다.
- 클러스터 범위 리소스는 환경별 AppProject의 `clusterResourceWhitelist` 허용 여부를 확인합니다.

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

태그는 소스 커밋 추적에 사용하고, Deployment에는 가능하면 `tag@sha256:digest` 형식으로
digest까지 고정합니다. 롤백할 수 있도록 배포에 사용한 digest를 Git 이력에 남깁니다.

## 변경 및 검증

1. 이슈를 만들고 작업 범위를 합의합니다.
2. `type/#이슈번호-설명` 형식으로 브랜치를 만듭니다.
3. 로컬에서 공백 오류와 Kubernetes API 검증을 수행합니다.
4. PR에서 Argo CD 영향 범위, Secret 포함 여부와 파괴적 변경을 확인합니다.
5. 병합 후 Argo CD Sync·Health와 실제 Pod·Service 상태를 확인합니다.

검증 예시:

```bash
git diff --check
kubectl apply --dry-run=server -f dev/<component>/
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
