# dev Actuator 8081 전환 인수인계

대상은 Gateway와 백엔드 서비스 9개, 총 10개 Deployment이다. 이 문서는
GitOps #149 / PR #154와 Backend PR #243의 적용 순서를 기록한다.
각 단계는 Git PR과 Argo CD로 반영한다. 수동 `kubectl apply`로 배포하지 않는다.

## 1. GitOps PR #154: 구·신 이미지 호환 준비

- 컨테이너에 `management: 8081` 포트를 미리 선언한다.
- startup/readiness/liveness probe는 컨테이너 내부에서
  `8081 /actuator/health`를 먼저 확인하고, 실패하면
  `8080 /actuator/health`를 확인하는 HTTP `exec` 방식이다.
  포트가 열렸다는 사실만 확인하는 TCP probe가 아니다.
- Gateway ALB 헬스체크는 `/`, 성공 코드는 `200,404`다.
  현재 Gateway의 `/`는 404이며, 이 경로는 Actuator 관리 포트 이동과
  무관하게 응답한다. 실제 애플리케이션 건강성 판단은 Pod의 HTTP probe가 맡는다.
- 이 단계에서 10개 Deployment가 롤링되므로 저트래픽 시간에 병합하고
  후속 검증 전에 Backend PR #243을 병합하지 않는다.

최신 PR #154 기준 사전 검증:

```bash
kubectl kustomize dev | grep -c 'name: management'                    # 10
kubectl kustomize dev | grep -c 'wget -q -T 2 -O /dev/null'           # 30
kubectl apply --dry-run=server -k dev
```

전체 렌더링의 `exec:` 개수에는 다른 워크로드의 probe도 포함되므로
30개 확인에는 위 `wget` 패턴을 사용한다. 2026-10-03 PR HEAD
`247eebb`에서 위 두 개수와 서버 dry-run 통과를 확인했다. 현행 구 이미지
10개에서 동일 `sh`/`wget` 명령이 모두 종료 코드 0으로 동작했다.

병합 직후 확인:

```bash
for s in auth member project order payment fulfillment notification search live gateway; do
  kubectl -n dev rollout status "deploy/fundit-$s" --timeout=300s
done
kubectl -n argocd get application fundit-dev
kubectl -n dev get targetgroupbindings
curl -sS -o /dev/null -w '%{http_code}\n' https://infrastudy.store/api/v1/lives/banner
```

통과 기준은 10개 Ready, Argo CD Synced/Healthy, Gateway ALB 타깃 모두
Healthy, 외부 API 정상 응답이다. `maxUnavailable: 0`만으로 무중단이
보장되는 것은 아니므로 ALB 타깃과 공개 API도 함께 본다.

## 2. Backend PR #243 병합 및 전수 확인

1단계가 안정화된 뒤 백엔드 담당자에게 병합 가능을 알린다. 이미지 자동갱신이
10개 서비스에 순차 적용되면 각 Deployment 이미지의 소스 SHA와 rollout을
확인한다. 모든 서비스에서 새 이미지의 8081 응답을 확인하기 전에는
3단계 PR을 병합하지 않는다.

```bash
for s in auth member project order payment fulfillment notification search live gateway; do
  kubectl -n dev get deploy "fundit-$s" -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
  kubectl -n dev rollout status "deploy/fundit-$s" --timeout=300s
done
```

각 Pod 내부에서 `127.0.0.1:8081/actuator/health`와
`127.0.0.1:8081/actuator/prometheus`가 모두 HTTP 200인지 별도로
확인한다. 새 이미지의 8080 `/actuator/health`는 404여야 한다.
이미지 태그만 바뀌었다는 사실은 검증 완료의 근거가 아니다.

## 3. 정식 8081 probe 및 PodMonitor

10개 새 이미지의 8081 응답 확인 후 후속 GitOps PR에서 세 probe를
`httpGet /actuator/health` / `port: management`로 전환하고
PodMonitor를 추가한다. Prometheus의 PodMonitor 선택 라벨과 서비스별
타깃 UP, JVM/Hikari/HTTP 메트릭을 확인한다. 8081을 공개 Ingress
경로나 Service에 추가하지 않는다.

## 복구와 주의 사항

- 어느 단계든 rollout, ALB 타깃, 공개 API가 실패하면 다음 단계로
  넘어가지 않는다. 변경 복구는 원인 확인 후 Git revert PR로 진행한다.
- `/`의 404는 애플리케이션 헬스 그 자체가 아니다. 전환 기간과
  이후 모두 Pod readiness와 ALB 타깃 건강성을 함께 확인한다.
- 이 문서는 PR #154의 최신 HTTP `exec` 구현을 기준으로 한다.
  과거 TCP probe 30개 또는 ALB `200-404`를 기대하는 절차는 사용하지 않는다.
