from unittest.mock import patch

import httpx

import github_client


def demonstrate_input_sanitization() -> None:
    malicious_repo = "Fork-Fly/../../user?access_token=steal-me"
    with patch.object(github_client.httpx, "get") as request:
        try:
            github_client.list_pull_requests("vidhu-hegde", malicious_repo)
        except ValueError as error:
            blocked_message = str(error)
        else:
            raise AssertionError("The malicious repository input was not blocked.")

    assert not request.called, "Untrusted input reached the GitHub HTTP client."
    print("PASS 1 - Input sanitization")
    print(f"  Attempt: repo={malicious_repo!r}")
    print(f"  Result: {blocked_message}")
    print("  Proof: no HTTP request was made.")


def demonstrate_error_disclosure() -> None:
    fake_token = "github_pat_FAKE_DEMO_SECRET"
    private_response = "database=/private/company.db token=github_pat_FAKE_DEMO_SECRET"
    response = httpx.Response(500, text=private_response)

    with (
        patch.object(github_client, "dotenv_values", return_value={"GITHUB_TOKEN": fake_token}),
        patch.object(github_client.httpx, "get", return_value=response),
    ):
        try:
            github_client.list_pull_requests("vidhu-hegde", "Fork-Fly")
        except ValueError as error:
            safe_message = str(error)
        else:
            raise AssertionError("The simulated GitHub failure did not raise an error.")

    assert fake_token not in safe_message, "The credential leaked into the client error."
    assert private_response not in safe_message, "The upstream response leaked into the client error."
    assert "/private/company.db" not in safe_message, "An internal path leaked into the client error."
    print("PASS 2 - Error disclosure protection")
    print("  Attempt: GitHub returns HTTP 500 with a fake token and private path in its body.")
    print(f"  Client receives: {safe_message}")
    print("  Proof: the fake token, private path, and response body are absent.")


if __name__ == "__main__":
    demonstrate_input_sanitization()
    demonstrate_error_disclosure()
    print("\nBoth Part 2 exploit demonstrations passed.")
