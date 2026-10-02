# CNPG PgBouncer Pooler 도입 및 카프카 파티션 증설 작업 결과

## 1. 개요
운영 환경 확장 및 부하 테스트(Load Test) 대비를 위해 다음 2가지 핵심 인프라 작업을 완료하였습니다:
1. **DB 커넥션 안전망 구축**: CloudNativePG(CNPG) `Pooler` (PgBouncer) 매니페스트 도입
2. **카프카 토픽 파티션 증설**: `notification.raised.v1`, `live.started.v1` 파티션을 1개에서 3개로 확장

---

## 2. 작업 내역 및 결과

### 1) CNPG PgBouncer Pooler (`fundit-dev-postgres-pooler`)
- **매니페스트 경로**: `dev/cnpg/pooler.yaml`
- **주요 설정**:
  - `instances: 2` (Multi-AZ 고가용성 이중화)
  - `poolMode: transaction` (트랜잭션 단위 커넥션 다중화)
  - `parameters.max_client_conn: "1000"` (클라이언트 최대 1,000개 수용)
  - `parameters.default_pool_size: "20"` (실제 DB 연결 20개 내외 압축)
  - `parameters.server_reset_query: "DISCARD ALL"` (Spring/HikariCP 트랜잭션 안전성)
  - `spec.template.spec.topologySpreadConstraints`: `topology.kubernetes.io/zone` 기반 Multi-AZ 자동 분산

### 2) 카프카 알림 토픽 파티션 증설 (1개 ➔ 3개)
- **실행 명령어**:
  ```bash
  kubectl exec -n kafka kafka-0 -- /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 --alter --topic notification.raised.v1 --partitions 3
  kubectl exec -n kafka kafka-0 -- /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 --alter --topic live.started.v1 --partitions 3
  ```
- **검증 결과 (`kafka-consumer-groups.sh`)**:
  - `notification.raised.v1`: Partition 0, 1, 2 정상 생성 및 할당 확인
  - `live.started.v1`: Partition 0, 1, 2 정상 생성 및 할당 확인
  - `notification-service` 파드가 3개 파티션을 유휴(Idle) 없이 전부 할당받아 소비 중임을 실측 완료
