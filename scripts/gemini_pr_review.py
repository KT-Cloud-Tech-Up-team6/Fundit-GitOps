import json
import os
import subprocess
import requests


def main():
    # 1. API 키 확인 (없으면 에러 대신 안전하게 스킵 안내)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("Notice: GEMINI_API_KEY is not configured in Repository Secrets. Skipping Gemini PR review.")
        return

    from google import genai
    from google.genai import types


    # 2. Git Diff 추출
    base_ref = os.environ.get("BASE_REF", "main")
    diff_command = f"git diff -U3 origin/{base_ref}...HEAD"
    try:
        diff_output = subprocess.check_output(diff_command, shell=True, text=True)
    except subprocess.CalledProcessError:
        diff_output = ""

    if not diff_output.strip():
        print("No changes found to review.")
        return

    # Diff 크기 제한 (타임아웃 및 과도한 토큰 방지)
    max_chars = 60000
    if len(diff_output) > max_chars:
        diff_output = diff_output[:max_chars] + "\n... (Diff truncated due to size limit)"

    # 3. 외부 가이드라인 파일(.github/review-rules.md) 로드
    rules_path = ".github/review-rules.md"
    if os.path.exists(rules_path):
        with open(rules_path, "r", encoding="utf-8") as f:
            guidelines = f.read()
    else:
        guidelines = "당신은 노련한 시니어 클라우드 인프라 및 GitOps 엔지니어입니다. 건설적이고 전문적인 코드 리뷰를 한국어로 제공하세요."

    # 4. Gemini 클라이언트 및 프롬프트 구성
    client = genai.Client(api_key=api_key)

    prompt = f"""
{guidelines}

### 출력 형식 지침 (반드시 준수):
반드시 아래 JSON 스키마 형식으로만 응답하세요:
{{
  "summary": "### 🤖 Gemini AI 요약\\n- 전체 변경 내역 3줄 요약\\n- 보안/운영 리스크 평가 및 총평",
  "inline_comments": [
    {{
      "path": "변경 파일 상대 경로 (예: apps/projects/dev-project.yaml)",
      "line": 42,
      "comment": "💡 **개선 제안**: 친절하고 명확한 피드백 본문"
    }}
  ]
}}

### 필수 주의사항 (반드시 엄수):
1. **코드 블록 단위 맥락 분석**: 단일 라인만 보지 말고 관련 코드 블록 전체의 문맥과 로직 흐름을 종합적으로 분석하세요.
2. **칭찬 및 사소한 코멘트 절대 금지**: 잘한 부분이나 정상적인 코드에 칭찬("좋은 구현입니다" 등)이나 단순 확인 코멘트를 절대 남기지 마세요.
3. **이상한 부분 / 잘못된 부분에만 코멘트 작성**: 문법 오류, 논리적 결함, 보안 취약점, 잘못되거나 위험한 설정, 리소스 낭비 등 실제 수정이 필요한 문제점에만 집중하세요.
4. **노이즈 최소화**: 특별한 결함이나 이상점이 없다면 inline_comments는 빈 배열([])로 두고 summary만 작성하세요.
5. inline_comments는 반드시 git diff에서 **새로 추가되거나 수정된 라인(+)**의 새 파일 기준 line 번호여야 합니다.

---
Git Diff:
```diff
{diff_output}
```
"""

    print("Requesting inline review from Gemini...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )

    try:
        review_data = json.loads(response.text)
    except Exception as e:
        print(f"JSON parsing error: {e}")
        review_data = {
            "summary": response.text,
            "inline_comments": []
        }

    repo = os.environ["REPO_NAME"]
    pr_num = os.environ["PR_NUMBER"]
    gh_token = os.environ["GITHUB_TOKEN"]
    commit_sha = os.environ["COMMIT_SHA"]

    summary_text = review_data.get("summary", "Gemini Code Review 완료")
    inline_comments = review_data.get("inline_comments", [])

    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 5. GitHub Review API 형식에 맞춰 코멘트 구성
    comments_payload = []
    for item in inline_comments:
        if "path" in item and "line" in item and "comment" in item:
            comments_payload.append({
                "path": item["path"],
                "line": int(item["line"]),
                "side": "RIGHT",
                "body": item["comment"]
            })

    review_payload = {
        "commit_id": commit_sha,
        "body": f"## 🤖 Gemini AI Code Review\n\n{summary_text}\n\n---\n*Automated review by Gemini Flash*",
        "event": "COMMENT",
        "comments": comments_payload
    }

    # 6. Review API 호출 (일괄 인라인 댓글 및 요약 등록)
    review_url = f"https://api.github.com/repos/{repo}/pulls/{pr_num}/reviews"
    res = requests.post(review_url, json=review_payload, headers=headers)

    if res.status_code == 200:
        print(f"Successfully posted review with {len(comments_payload)} inline comments!")
    else:
        print(f"Review API call returned {res.status_code}: {res.text}")
        print("Fallback: posting summary comment only...")
        # 라인 번호 불일치 등 422 에러 발생 시 fallback으로 일반 코멘트 등록
        fallback_url = f"https://api.github.com/repos/{repo}/issues/{pr_num}/comments"
        fallback_body = f"## 🤖 Gemini AI Code Review\n\n{summary_text}\n\n"
        if inline_comments:
            fallback_body += "### 💬 인라인 피드백 목록\n"
            for item in inline_comments:
                fallback_body += f"- **`{item.get('path')}:{item.get('line')}`**: {item.get('comment')}\n"
        requests.post(fallback_url, json={"body": fallback_body}, headers=headers)


if __name__ == "__main__":
    main()
