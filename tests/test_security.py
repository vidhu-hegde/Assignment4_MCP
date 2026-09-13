import unittest
from unittest.mock import patch

import httpx

import github_client


class InputSanitizationTests(unittest.TestCase):
    def test_injection_payloads_are_blocked_before_http_request(self) -> None:
        attacks = [
            ("vidhu-hegde/../../users", "Fork-Fly"),
            ("vidhu-hegde", "Fork-Fly?per_page=100&token=steal-me"),
            ("vidhu-hegde", "../Fork-Fly"),
            ("vidhu-hegde%2Fadmin", "Fork-Fly"),
            ("vidhu-hegde\nX-Injected: true", "Fork-Fly"),
        ]
        with patch.object(github_client.httpx, "get") as request:
            for owner, repo in attacks:
                with self.subTest(owner=owner, repo=repo):
                    with self.assertRaises(ValueError):
                        github_client.list_pull_requests(owner, repo)
            request.assert_not_called()

    def test_invalid_types_and_pagination_are_blocked(self) -> None:
        with patch.object(github_client.httpx, "get") as request:
            for page in (0, -1, True, "1", 1.5):
                with self.subTest(page=page):
                    with self.assertRaises(ValueError):
                        github_client.list_pull_requests("vidhu-hegde", "Fork-Fly", page=page)
            with self.assertRaises(ValueError):
                github_client.list_pull_requests("vidhu-hegde", "Fork-Fly", per_page=31)
            request.assert_not_called()


class ErrorDisclosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_token = "github_pat_FAKE_TEST_SECRET"
        self.private_body = "database=/private/company.db token=github_pat_FAKE_TEST_SECRET"

    def assert_safe_error(self, error: ValueError) -> None:
        message = str(error)
        self.assertNotIn(self.fake_token, message)
        self.assertNotIn(self.private_body, message)
        self.assertNotIn("/private/company.db", message)

    def test_upstream_error_bodies_are_not_disclosed(self) -> None:
        with patch.object(
            github_client, "dotenv_values", return_value={"GITHUB_TOKEN": self.fake_token}
        ):
            for status_code in (301, 401, 403, 404, 429, 500):
                response = httpx.Response(status_code, text=self.private_body)
                with self.subTest(status_code=status_code), patch.object(
                    github_client.httpx, "get", return_value=response
                ):
                    with self.assertRaises(ValueError) as raised:
                        github_client.list_pull_requests("vidhu-hegde", "Fork-Fly")
                    self.assert_safe_error(raised.exception)

    def test_network_exception_details_are_not_disclosed(self) -> None:
        with patch.object(
            github_client, "dotenv_values", return_value={"GITHUB_TOKEN": self.fake_token}
        ):
            for failure in (
                httpx.ReadTimeout(self.private_body),
                httpx.ConnectError(self.private_body),
            ):
                with self.subTest(failure=type(failure).__name__), patch.object(
                    github_client.httpx, "get", side_effect=failure
                ):
                    with self.assertRaises(ValueError) as raised:
                        github_client.list_pull_requests("vidhu-hegde", "Fork-Fly")
                    self.assert_safe_error(raised.exception)


if __name__ == "__main__":
    unittest.main()
