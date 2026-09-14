## PR 개요
> 배포 정의 변경 요약

- 연관 이슈: close #

---

## 변경 유형 (Type of Change)
- [ ] 새로운 서비스/컴포넌트 매니페스트 추가 (New Feature)
- [ ] 기존 매니페스트 설정 수정 (Configuration Change)
- [ ] 매니페스트 삭제 또는 마이그레이션 (Deprecation/Removal)
- [ ] 배포 오류 또는 sync 실패 수정 (Bug Fix)
- [ ] 문서 수정 (Documentation)

---

## 영향 받는 환경 및 서비스
- **환경 (Environment)**:
  - [ ] `dev`
  - [ ] `staging` (미사용, 선택해도 배포 안 됨)
  - [ ] `prod`
- **영향 받는 서비스/컴포넌트**:
  - 

---

## 변경 내용 확인
> `kubectl diff`, `kustomize build`, ArgoCD diff 등 확인 결과

```text

```

- [ ] **파괴적 변경 여부**: 리소스 삭제·재생성 있으면 체크, 영향도 명시
  - 삭제/재생성 대상: 

---

## 체크리스트 (Checklist)
- [ ] 매니페스트 문법(YAML lint 등) 확인
- [ ] Secret(비밀키, 패스워드 등) 하드코딩·커밋 없음 확인
- [ ] ArgoCD sync 상태 확인 또는 확인 예정
- [ ] 관련 문서 업데이트 반영

---

## 테스트 및 검증 결과 (스크린샷 등)
> ArgoCD 화면, `kubectl get` 결과 등 첨부
