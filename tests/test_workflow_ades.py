import unittest
from unittest.mock import Mock, patch

from system_tests.ades import ADESClient
from system_tests.cwl_loader import CWLFile


class TestEODHPClient(unittest.TestCase):
    def test_init(self):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )

        assert ades_client.url == "https://test-ades-url"
        assert ades_client.username == "username"
        assert ades_client.user_url == "https://test-ades-url/username"

    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_check_status(self, mock_logger, MockRequests):
        ades_client = ADESClient("https://test-ades-url", "username")
        # Configure mocks
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
        # This will take 5 seconds to complete due to sleep command when waiting for status change
        MockRequests.get.side_effect = [mock_response_1, mock_response_2]

        ades_client.check_status()

        calls = mock_logger.info.call_args_list

        assert calls[4][0][0] == "ADES is running"

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

        assert calls[1][0][0] == "API token tested successfully"

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

        assert calls[1][0][0] == "Workflow %s undeployed successfully"
        assert calls[1][0][1] == "workflow_id"

    def test_check_deployment_status_link(self):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )

        raw_cwl = {"$graph": [{"id": "workflow_id"}]}

        cwl_file = CWLFile(raw_cwl, {}, "")

        headers = {"Location": "https://test-ades-url/username/ogc-api/processes/workflow_id"}

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

        assert calls[1][0][0] == "Workflow %s deployed successfully"
        assert calls[1][0][1] == "workflow_id"

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

        assert calls[1][0][0] == "Workflow %s deployed successfully"
        assert calls[1][0][1] == "workflow_id"

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

        assert calls[1][0][0] == "Workflow %s is available"
        assert calls[1][0][1] == "workflow_id"

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

        assert job_id == "job_id"

        calls = mock_logger.info.call_args_list

        assert calls[2][0][0] == "Workflow: %s executed under job: %s"
        assert calls[2][0][1] == "workflow_id"
        assert calls[2][0][2] == "job_id"

    @patch("system_tests.ades.ADESClient.check_logs_access")  # Mock the requests module
    @patch("system_tests.ades.requests")  # Mock the requests module
    @patch("system_tests.ades.logger")  # Mock the logger module
    def test_monitor_workflow(self, mock_logger, MockRequests, mock_check_logs_access):
        ades_client = ADESClient(
            "https://test-ades-url",
            "username",
        )
        api_token = "valid-api-token"
        ades_client.set_api_token(api_token)

        # Configure mocks
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

        # This will take 5 seconds to run as there is a sleep command while monitoring the workflow
        results_link = ades_client.monitor_workflow("job_id")

        assert results_link == "https:/test-ades-url/username/jobs/job_id/results"

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Workflow still running, message: %s"
        assert calls[1][0][1] == "process is running"
        assert calls[2][0][0] == "Workflow completed, job id: %s"
        assert calls[2][0][1] == "job_id"

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

        ades_client.check_logs_access(links)

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Logs are accessible"
