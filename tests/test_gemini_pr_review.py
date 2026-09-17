import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# scripts 디렉터리를 sys.path에 추가하여 모듈 import 가능하게 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import gemini_pr_review


class TestGeminiPrReview(unittest.TestCase):
    """Gemini PR Review 스크립트 단위 및 Mock 테스트"""

    def setUp(self):
        # 환경 변수 초기화
        self.orig_env = os.environ.copy()
        os.environ["REPO_NAME"] = "test-org/test-repo"
        os.environ["PR_NUMBER"] = "42"
        os.environ["GITHUB_TOKEN"] = "mock-token"
        os.environ["COMMIT_SHA"] = "abc1234"
        os.environ["HEAD_SHA"] = "abc1234"
        os.environ["BASE_REF"] = "main"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_skip_when_no_api_key(self):
        """GEMINI_API_KEY가 설정되지 않은 경우 에러 없이 스킵되는지 검증"""
        os.environ["GEMINI_API_KEY"] = ""
        with patch("builtins.print") as mock_print:
            gemini_pr_review.main()
            mock_print.assert_any_call(
                "Notice: GEMINI_API_KEY is not configured in Repository Secrets. Skipping Gemini PR review."
            )

    @patch("gemini_pr_review.subprocess.check_output")
    def test_git_diff_called_with_list_args(self, mock_subprocess):
        """subprocess.check_output이 shell=True 없이 인자 배열(List)로 안전하게 호출되는지 검증"""
        os.environ["GEMINI_API_KEY"] = "mock-api-key"
        mock_subprocess.return_value = ""

        mock_google = MagicMock()
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_google.genai}):
            with patch("builtins.print") as mock_print:
                gemini_pr_review.main()
                mock_subprocess.assert_called_once_with(
                    ["git", "diff", "-U3", "origin/main...abc1234"],
                    text=True,
                    timeout=30,
                )
                mock_print.assert_any_call("No changes found to review.")

    @patch("gemini_pr_review.requests.post")
    @patch("gemini_pr_review.subprocess.check_output")
    def test_review_posted_successfully(self, mock_subprocess, mock_requests_post):
        """Gemini 응답 파싱 및 GitHub Review API 정상 호출 검증"""
        os.environ["GEMINI_API_KEY"] = "mock-api-key"
        mock_subprocess.return_value = "diff --git a/test.py b/test.py\n+print('hello')"

        # Mock Gemini Client 및 응답 텍스트
        mock_response = MagicMock()
        mock_response.text = '{"summary": "Test Summary", "inline_comments": []}'
        mock_gemini_client = MagicMock()
        mock_gemini_client.models.generate_content.return_value = mock_response

        # Mock requests.post (GitHub Review API 성공)
        mock_http_res = MagicMock()
        mock_http_res.status_code = 200
        mock_requests_post.return_value = mock_http_res

        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_gemini_client

        with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
            gemini_pr_review.main()

        # Review API가 timeout=30과 함께 정상 호출되었는지 확인
        mock_requests_post.assert_called_once()
        call_kwargs = mock_requests_post.call_args[1]
        self.assertEqual(call_kwargs.get("timeout"), 30)

    @patch("gemini_pr_review.requests.post")
    @patch("gemini_pr_review.subprocess.check_output")
    def test_fallback_comment_on_review_api_failure(self, mock_subprocess, mock_requests_post):
        """1차 Review API 실패 시 Fallback Comment API가 정상 호출되는지 검증"""
        os.environ["GEMINI_API_KEY"] = "mock-api-key"
        mock_subprocess.return_value = "diff --git a/test.py b/test.py\n+print('hello')"

        mock_response = MagicMock()
        mock_response.text = '{"summary": "Test Summary", "inline_comments": []}'
        mock_gemini_client = MagicMock()
        mock_gemini_client.models.generate_content.return_value = mock_response

        # 1차 호출: 422 실패, 2차 Fallback 호출: 201 성공
        review_fail_res = MagicMock()
        review_fail_res.status_code = 422
        review_fail_res.text = "Unprocessable Entity"

        fallback_success_res = MagicMock()
        fallback_success_res.status_code = 201

        mock_requests_post.side_effect = [review_fail_res, fallback_success_res]

        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_gemini_client

        with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
            gemini_pr_review.main()

        # 2번의 API 호출(1차 Review -> 2차 Fallback)이 발생했는지 확인
        self.assertEqual(mock_requests_post.call_count, 2)

    @patch("gemini_pr_review.requests.post")
    @patch("gemini_pr_review.subprocess.check_output")
    def test_failure_exit_when_both_apis_fail(self, mock_subprocess, mock_requests_post):
        """1차와 Fallback API 모두 실패 시 sys.exit(1)로 실패 처리되는지 검증"""
        os.environ["GEMINI_API_KEY"] = "mock-api-key"
        mock_subprocess.return_value = "diff --git a/test.py b/test.py\n+print('hello')"

        mock_response = MagicMock()
        mock_response.text = '{"summary": "Test Summary", "inline_comments": []}'
        mock_gemini_client = MagicMock()
        mock_gemini_client.models.generate_content.return_value = mock_response

        # 둘 다 실패
        fail_res = MagicMock()
        fail_res.status_code = 500
        fail_res.text = "Internal Server Error"
        mock_requests_post.return_value = fail_res

        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_gemini_client

        with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
            with self.assertRaises(SystemExit) as cm:
                gemini_pr_review.main()
            self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
