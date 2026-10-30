import unittest
from unittest.mock import Mock, patch

import pytest

from system_tests.ades import ADESClient
from system_tests.cwl_loader import CWLFile
from system_tests.exceptions import WorkflowDeploymentException, WorkflowMonitorException


class TestEODHPClient(unittest.TestCase):
    def test_init(self) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )

        assert ades_client.url == "https://test-ades-url"
        assert ades_client.workspace == "workspace"
        assert ades_client.user_url == "https://test-ades-url/workspace"

    @patch("system_tests.ades.time.sleep")  # Mock the requests module
    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_status(self, mock_logger: Mock, MockRequests: Mock, mock_sleep: Mock) -> None:
        ades_client = ADESClient("https://test-ades-url", "workspace")
        # Configure mocks
        mock_sleep.return_value = None
        mock_response_1 = Mock()
        mock_response_1.status_code = 404
        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "features": [
                {
                    "id": "test_item",
                    "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link1"}],
                },
                {
                    "id": "test_item2",
                    "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link2"}],
                },
            ]
        }
        MockRequests.get.side_effect = [mock_response_1, mock_response_2]

        ades_client.check_status()

        calls = mock_logger.info.call_args_list

        assert calls[4][0][0] == "ADES is running"

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_api_token(self, mock_logger: Mock, MockRequests: Mock) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 200
        MockRequests.get.return_value = mock_response

        ades_client.check_api_token()

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "API token tested successfully"

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_undeploy_workflow(self, mock_logger: Mock, MockRequests: Mock) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 204
        MockRequests.delete.return_value = mock_response

        ades_client.undeploy_workflow("workflow_id")

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Workflow %s undeployed successfully"
        assert calls[1][0][1] == "workflow_id"

    def test_check_deployment_status_link_pass(self) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}

        cwl_file = CWLFile(raw_cwl, {}, "")

        headers = {"Location": "https://test-ades-url/workspace/processes/workflow_id"}

        # Check no error is raised
        ades_client.check_deployment_status_link(headers, cwl_file)

    def test_check_deployment_status_link_fail(self) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}

        cwl_file = CWLFile(raw_cwl, {}, "")

        headers = {"Location": "https://test-ades-url/workspace/processes/wrong-workflow"}

        # Check raises error
        with pytest.raises(WorkflowDeploymentException):
            ades_client.check_deployment_status_link(headers, cwl_file)

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    @patch(
        "system_tests.ades.ADESClient.check_deployment_status_link"
    )  # Mock the check_deployment_status_link function
    def test_deploy_workflow_url(self, mock_check_link: Mock, mock_logger: Mock, MockRequests: Mock) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 201
        MockRequests.post.return_value = mock_response

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}

        cwl_file = CWLFile(raw_cwl, {}, "https://workflow-location/path/to/workflow.cwl")

        ades_client.deploy_workflow(cwl_file)

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Workflow %s deployed successfully"
        assert calls[1][0][1] == "workflow_id"

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    @patch(
        "system_tests.ades.ADESClient.check_deployment_status_link"
    )  # Mock the check_deployment_status_link function
    @patch("system_tests.ades.time.sleep")  # Mock the time.sleep function
    def test_deploy_workflow_url_too_many_requests(
        self, mock_time_sleep: Mock, mock_check_link: Mock, mock_logger: Mock, MockRequests: Mock
    ) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_time_sleep.return_value = None
        mock_response_1 = Mock()
        mock_response_1.status_code = 429
        mock_response_2 = Mock()
        mock_response_2.status_code = 201

        MockRequests.post.side_effect = [mock_response_1, mock_response_2]

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}

        cwl_file = CWLFile(raw_cwl, {}, "https://workflow-location/path/to/workflow.cwl")

        ades_client.deploy_workflow(cwl_file)

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Workflow %s deployed successfully"
        assert calls[1][0][1] == "workflow_id"

        assert mock_time_sleep.call_count == 1

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    @patch(
        "system_tests.ades.ADESClient.check_deployment_status_link"
    )  # Mock the check_deployment_status_link function
    def test_deploy_workflow_file(self, mock_check_link: Mock, mock_logger: Mock, MockRequests: Mock) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 201
        MockRequests.post.return_value = mock_response

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}

        cwl_file = CWLFile(raw_cwl, {}, "examples/convert-url-app.cwl")

        ades_client.deploy_workflow(cwl_file)

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Workflow %s deployed successfully"
        assert calls[1][0][1] == "workflow_id"

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_deployment_status(self, mock_logger: Mock, MockRequests: Mock) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "workflow_id",
            "links": [
                {
                    "title": "Execute End Point",
                    "href": "https://test-ades-url/workspace/processes/workflow_id/execution",
                }
            ],
        }
        MockRequests.get.return_value = mock_response

        ades_client.check_deployment_status("workflow_id")

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Workflow %s is available"
        assert calls[1][0][1] == "workflow_id"

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_execute_workflow(self, mock_logger: Mock, MockRequests: Mock) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"jobID": "job_id", "status": "running"}
        MockRequests.post.return_value = mock_response

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}
        raw_inputs = {"inputs": {"key": "value"}}

        cwl_file = CWLFile(raw_cwl, raw_inputs, "path/to/workflow.cwl")

        job_id = ades_client.execute_workflow(cwl_file)

        assert job_id == "job_id"

        calls = mock_logger.info.call_args_list

        assert calls[2][0][0] == "Workflow: %s executed under job: %s"
        assert calls[2][0][1] == "workflow_id"
        assert calls[2][0][2] == "job_id"

    @patch("system_tests.ades.time.sleep")  # Mock the requests module
    @patch("system_tests.ades.ADESClient.check_logs_access")  # Mock the requests module
    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_monitor_workflow(
        self, mock_logger: Mock, MockRequests: Mock, mock_check_logs_access: Mock, mock_sleep: Mock
    ) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_sleep.return_value = None
        mock_check_logs_access.return_value = None
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "status": "running",
            "message": "process is running",
            "links": [],
        }
        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "status": "successful",
            "links": [
                {
                    "title": "Result location",
                    "href": "https:/test-ades-url/workspace/jobs/job_id/results",
                },
                {
                    "title": "Tool log node_stage_out.log",
                    "href": "https://test-ades-url/temp/workflow/stage-out.log",
                },
            ],
        }
        MockRequests.get.side_effect = [mock_response_1, mock_response_2]

        results_link = ades_client.monitor_workflow("job_id")

        assert results_link == "https:/test-ades-url/workspace/jobs/job_id/results"

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Workflow still running, message: %s"
        assert calls[1][0][1] == "process is running"
        assert calls[2][0][0] == "Workflow completed, job id: %s"
        assert calls[2][0][1] == "job_id"

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_logs_access(self, mock_logger: Mock, MockRequests: Mock) -> None:
        ades_client = ADESClient(
            "https://test-ades-url",
            "workspace",
        )

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = None
        MockRequests.get.return_value = mock_response

        links = [
            {
                "title": "Result location",
                "href": "https:/test-ades-url/workspace/jobs/job_id/results",
            },
            {
                "title": "Tool log node_stage_out.log",
                "href": "https://test-ades-url/temp/workflow/stage-out.log",
            },
        ]

        ades_client.check_logs_access("https:/test-ades-url/workspace/jobs/job_id/results", links)

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Logs are accessible"


def job_response(status: str, message: str = "") -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"status": status, "message": message, "links": []}
    return response


class TestMonitorWorkflowFailure(unittest.TestCase):
    def setUp(self) -> None:
        self.ades_client = ADESClient("https://test-ades-url", "workspace", api_token="valid-api-token")

    @patch("system_tests.ades.time.sleep")
    @patch("system_tests.ades.requests")
    def test_expected_failure(self, MockRequests: Mock, mock_sleep: Mock) -> None:
        MockRequests.get.side_effect = [
            job_response("running", "process is running"),
            job_response("failed", "Execution failed: [step fail_on_purpose] completed permanentFail"),
        ]

        message = self.ades_client.monitor_workflow_failure("job_id", "fail_on_purpose")

        assert message == "Execution failed: [step fail_on_purpose] completed permanentFail"
        assert mock_sleep.call_count == 1

    @patch("system_tests.ades.requests")
    def test_failure_without_expected_message(self, MockRequests: Mock) -> None:
        MockRequests.get.return_value = job_response("failed", "Execution failed")

        assert self.ades_client.monitor_workflow_failure("job_id") == "Execution failed"

    @patch("system_tests.ades.requests")
    def test_failure_with_other_message(self, MockRequests: Mock) -> None:
        MockRequests.get.return_value = job_response("failed", "Execution failed")

        with pytest.raises(WorkflowMonitorException, match="does not contain 'fail_on_purpose'"):
            self.ades_client.monitor_workflow_failure("job_id", "fail_on_purpose")

    @patch("system_tests.ades.requests")
    def test_failure_with_stack_trace(self, MockRequests: Mock) -> None:
        MockRequests.get.return_value = job_response(
            "failed", "Exception during execution...\nTraceback (most recent call last):\n fail_on_purpose"
        )

        with pytest.raises(WorkflowMonitorException, match="stack trace"):
            self.ades_client.monitor_workflow_failure("job_id", "fail_on_purpose")

    @patch("system_tests.ades.requests")
    def test_unexpected_success(self, MockRequests: Mock) -> None:
        MockRequests.get.return_value = job_response("successful")

        with pytest.raises(WorkflowMonitorException, match="expected to fail"):
            self.ades_client.monitor_workflow_failure("job_id")

    @patch("system_tests.ades.time.sleep")
    @patch("system_tests.ades.requests")
    def test_hang_times_out(self, MockRequests: Mock, mock_sleep: Mock) -> None:
        self.ades_client.monitor_timeout = 0
        MockRequests.get.return_value = job_response("running")

        with pytest.raises(WorkflowMonitorException, match="timed out"):
            self.ades_client.monitor_workflow_failure("job_id")

    @patch("system_tests.ades.requests")
    def test_status_error(self, MockRequests: Mock) -> None:
        response = Mock()
        response.status_code = 500
        MockRequests.get.return_value = response

        with pytest.raises(WorkflowMonitorException, match="Failed to monitor job"):
            self.ades_client.monitor_workflow_failure("job_id")
