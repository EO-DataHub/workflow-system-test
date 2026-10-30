from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from system_tests.__main__ import cli
from system_tests.cwl_loader import CWLFile

ARGS = [
    "workflow",
    "https://test-ades-url",
    "https://test-catalogue-url",
    "examples/failing-step-app.cwl",
    "examples/failing-step-app-inputs.json",
]


@pytest.fixture
def clients(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Mock, Mock]]:
    monkeypatch.setenv("API_TOKEN", "valid-api-token")
    with (
        patch("system_tests.__main__.ADESClient") as MockADESClient,
        patch("system_tests.__main__.EODHPClient") as MockEODHPClient,
        patch("system_tests.__main__.FileCWLLoader") as MockFileCWLLoader,
        patch("system_tests.__main__.time.sleep"),
    ):
        MockFileCWLLoader.return_value.load_cwl.return_value = CWLFile(
            {"$graph": [{"id": "test-failing-step"}]}, {"inputs": {}}, "examples/failing-step-app.cwl"
        )
        yield MockADESClient.return_value, MockEODHPClient.return_value


def test_expect_failure(clients: tuple[Mock, Mock]) -> None:
    ades_client, eodhp_client = clients

    result = CliRunner().invoke(cli, [*ARGS, "--expect-failure", "--expect-message", "fail_on_purpose"])

    assert result.exit_code == 0, result.output
    ades_client.monitor_workflow_failure.assert_called_once_with(
        ades_client.execute_workflow.return_value, "fail_on_purpose"
    )
    ades_client.monitor_workflow.assert_not_called()
    eodhp_client.check_s3_access_token.assert_not_called()
    ades_client.undeploy_workflow.assert_called_once_with("test-failing-step")


def test_expect_failure_undeploys_when_check_fails(clients: tuple[Mock, Mock]) -> None:
    ades_client, _ = clients
    ades_client.monitor_workflow_failure.side_effect = RuntimeError("Workflow timed out")

    result = CliRunner().invoke(cli, [*ARGS, "--expect-failure"])

    assert result.exit_code != 0
    ades_client.undeploy_workflow.assert_called_once_with("test-failing-step")


def test_expect_message_requires_expect_failure(clients: tuple[Mock, Mock]) -> None:
    ades_client, _ = clients

    result = CliRunner().invoke(cli, [*ARGS, "--expect-message", "fail_on_purpose"])

    assert result.exit_code == 2
    ades_client.execute_workflow.assert_not_called()


def test_success_mode_unchanged(clients: tuple[Mock, Mock]) -> None:
    ades_client, eodhp_client = clients

    result = CliRunner().invoke(cli, ARGS)

    assert result.exit_code == 0, result.output
    ades_client.monitor_workflow.assert_called_once()
    ades_client.monitor_workflow_failure.assert_not_called()
    eodhp_client.check_s3_access_token.assert_called_once()
