import unittest
from unittest.mock import Mock, patch

import pytest

from system_tests.ades import ADESClient
from system_tests.cwl_loader import CWLFile
from system_tests.exceptions import WorkflowDeploymentException


class TestEODHPClient(unittest.TestCase):
    def test_init(self):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )

        self.assertEqual(ades_client.url, "https://test-ades-url")
        self.assertEqual(ades_client.username, "username")
        self.assertEqual(ades_client.user_url, "https://test-ades-url/username")

    @patch("system_tests.ades.time.sleep")  # Mock the requests module
    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_status(self, mock_logger, MockRequests, mock_sleep):
        ades_client = ADESClient("https://test-ades-url", "username")
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

        self.assertEqual("ADES is running", calls[4][0][0])

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_api_token(self, mock_logger, MockRequests):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 200
        MockRequests.get.return_value = mock_response

        ades_client.check_api_token()

        calls = mock_logger.info.call_args_list

        self.assertEqual("API token tested successfully", calls[1][0][0])

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_undeploy_workflow(self, mock_logger, MockRequests):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 204
        MockRequests.delete.return_value = mock_response

        ades_client.undeploy_workflow("workflow_id")

        calls = mock_logger.info.call_args_list

        self.assertEqual("Workflow %s undeployed successfully", calls[1][0][0])
        self.assertEqual("workflow_id", calls[1][0][1])

    def test_check_deployment_status_link_pass(self):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}

        cwl_file = CWLFile(raw_cwl, {}, "")

        headers = {"Location": "https://test-ades-url/username/ogc-api/processes/workflow_id"}

        # Check no error is raised
        ades_client.check_deployment_status_link(headers, cwl_file)

    def test_check_deployment_status_link_fail(self):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}

        cwl_file = CWLFile(raw_cwl, {}, "")

        headers = {"Location": "https://test-ades-url/username/ogc-api/processes/wrong-workflow"}

        # Check raises error
        with pytest.raises(WorkflowDeploymentException):
            ades_client.check_deployment_status_link(headers, cwl_file)

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    @patch("system_tests.ades.ADESClient.check_deployment_status_link")  # Mock the logger module
    def test_deploy_workflow_url(self, mock_check_link, mock_logger, MockRequests):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
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

        self.assertEqual("Workflow %s deployed successfully", calls[1][0][0])
        self.assertEqual("workflow_id", calls[1][0][1])

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    @patch("system_tests.ades.ADESClient.check_deployment_status_link")  # Mock the logger module
    def test_deploy_workflow_file(self, mock_check_link, mock_logger, MockRequests):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
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

        self.assertEqual("Workflow %s deployed successfully", calls[1][0][0])
        self.assertEqual("workflow_id", calls[1][0][1])

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_deployment_status(self, mock_logger, MockRequests):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
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
                    "href": "https://test-ades-url/username/ogc-api/processes/workflow_id/execution",
                }
            ],
        }
        MockRequests.get.return_value = mock_response

        ades_client.check_deployment_status("workflow_id")

        calls = mock_logger.info.call_args_list

        self.assertEqual("Workflow %s is available", calls[1][0][0])
        self.assertEqual("workflow_id", calls[1][0][1])

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_execute_workflow(self, mock_logger, MockRequests):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
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

        self.assertEqual("job_id", job_id)

        calls = mock_logger.info.call_args_list

        self.assertEqual("Workflow: %s executed under job: %s", calls[2][0][0])
        self.assertEqual("workflow_id", calls[2][0][1])
        self.assertEqual("job_id", calls[2][0][2])

    @patch("system_tests.ades.time.sleep")  # Mock the requests module
    @patch("system_tests.ades.ADESClient.check_logs_access")  # Mock the requests module
    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_monitor_workflow(self, mock_logger, MockRequests, mock_check_logs_access, mock_sleep):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
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
                    "href": "https:/test-ades-url/username/jobs/job_id/results",
                },
                {
                    "title": "Tool log node_stage_out.log",
                    "href": "https://test-ades-url/temp/workflow/stage-out.log",
                },
            ],
        }
        MockRequests.get.side_effect = [mock_response_1, mock_response_2]

        results_link = ades_client.monitor_workflow("job_id")

        self.assertEqual("https:/test-ades-url/username/jobs/job_id/results", results_link)

        calls = mock_logger.info.call_args_list

        self.assertEqual("Workflow still running, message: %s", calls[1][0][0])
        self.assertEqual("process is running", calls[1][0][1])
        self.assertEqual("Workflow completed, job id: %s", calls[2][0][0])
        self.assertEqual("job_id", calls[2][0][1])

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_logs_access(self, mock_logger, MockRequests):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = None
        MockRequests.get.return_value = mock_response

        links = [
            {
                "title": "Result location",
                "href": "https:/test-ades-url/username/jobs/job_id/results",
            },
            {
                "title": "Tool log node_stage_out.log",
                "href": "https://test-ades-url/temp/workflow/stage-out.log",
            },
        ]

        ades_client.check_logs_access("https:/test-ades-url/username/jobs/job_id/results", links)

        calls = mock_logger.info.call_args_list

        self.assertEqual("Logs are accessible", calls[1][0][0])
