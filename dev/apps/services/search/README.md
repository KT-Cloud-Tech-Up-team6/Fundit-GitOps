# Search 배포 전제조건

`fundit-search`는 CNPG의 `app` 데이터베이스 안에서 `search` 스키마를 사용합니다.
Flyway가 스키마와 이력 테이블을 생성하며 다른 서비스의 migration과 분리됩니다.

다음 의존성이 먼저 준비되어야 합니다.

- `dev/fundit-dev-postgres-app`: CNPG가 관리하는 DB 접속 Secret
- `dev/fundit-backend-secrets`: `internal-api-key` 키
- `kafka/kafka`: `kafka.kafka.svc.cluster.local:9092`에서 접근 가능한 Kafka
- CNPG PostgreSQL의 `pg_trgm` 확장

Secret의 실제 값은 Git과 이 문서에 기록하지 않습니다.

## 검색 저장소 및 Kafka

별도 Elasticsearch/OpenSearch는 사용하지 않고 PostgreSQL `pg_trgm`과 GIN 인덱스를 사용합니다.
Flyway V1이 `pg_trgm` 확장을 생성하며 CNPG의 app DB에서 사용 가능한 것을 확인했습니다.

Search 서비스는 다음 토픽을 소비합니다.

- `project.approved.v1`, `project.updated.v1`
- `project.wished.v1`, `project.unwished.v1`
- `funding.succeeded.v1`, `funding.goal-failed.v1`

consumer group은 `search-service`이며 `auto-offset-reset=earliest`입니다.
최초 배포 시 보존 중인 과거 이벤트를 재생하여 검색 read model을 구성할 수 있습니다.

## Gateway 경로

Gateway의 `SEARCH_SERVICE_BASE_URL`은 `http://fundit-search-svc:8080`을 사용합니다.

- `/api/v1/home/**`
- `/api/v1/categories/**`
- `/api/v1/search/**`

## 배포 이미지

Backend `develop`의 성공한 search-service CI/CD 결과를 tag와 digest로 고정합니다.

- commit: `11c61dedb7fe6248d41ab1f00979b80577590301`
- CD run: `35696682430`
