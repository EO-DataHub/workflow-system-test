import importlib
import json
import os
import unittest
from unittest.mock import Mock, patch

import requests_mock


class TestWorkflowLocal(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["WORKFLOW_FILE"] = "examples/convert-url-app.cwl"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    def test_get_workflow_id_local_file(self):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import get_workflow_id

        assert get_workflow_id() == "test-convert-url"

    def test_generate_workflow_address_local(self):
        os.environ["WORKFLOW_FILE"] = "examples/convert-url-app.cwl"
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import generate_workflow_address

        assert generate_workflow_address() == "examples/convert-url-app.cwl"


class TestWorkflowRemote(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["GITHUB_REPO"] = "test-repo"
        os.environ["GITHUB_BRANCH"] = "main"
        os.environ["WORKFLOW_FILE"] = "examples/convert-url-app.cwl"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @patch("github.Github")
    def test_get_workflow_id_remote_file(self, mockGithub):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import get_workflow_id

        # Configure mocks
        mock_github_instance = mockGithub.return_value
        mock_repo = Mock()
        mock_contents = Mock()
        # To mock Github access we just load local file instead
        with open("examples/convert-url-app.cwl", "r") as f:
            mock_contents.decoded_content = f.read()
            mock_repo.get_contents.return_value = mock_contents
        mock_github_instance.get_repo.return_value = mock_repo
        assert get_workflow_id() == "test-convert-url"

    def test_generate_workflow_address_remote(self):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import generate_workflow_address

        assert (
            generate_workflow_address()
            == "https://raw.githubusercontent.com/test-repo/main/examples/convert-url-app.cwl"
        )


class TestRefreshToken(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["AUTH_TOKEN_API_URL"] = "https://oauth2-token-url.com"
        os.environ["CLIENT_ID"] = "client_id"
        os.environ["CLIENT_SECRET"] = "client_secret"
        os.environ["USERNAME"] = "username"
        os.environ["PASSWORD"] = "password"
        os.environ["DEBUG"] = "false"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @requests_mock.Mocker()
    def test_refresh_token(self, mock):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import get_refresh_token

        # Configure mocks
        mock.post(
            "https://oauth2-token-url.com",
            status_code=200,
            json=lambda request, context: {"refresh_token": "test-refresh-token"},
        )
        assert get_refresh_token() == "test-refresh-token"


class TestAccessToken(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["AUTH_TOKEN_API_URL"] = "https://oauth2-token-url.com"
        os.environ["CLIENT_ID"] = "client_id"
        os.environ["CLIENT_SECRET"] = "client_secret"
        os.environ["DEBUG"] = "false"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @requests_mock.Mocker()
    def test_refresh_token(self, mock):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import get_access_token

        # Configure mocks
        mock_refresh_token = "valid-refresh-token"
        mock.post(
            "https://oauth2-token-url.com",
            status_code=200,
            json=lambda request, context: {"access_token": "test-access-token"},
        )
        assert get_access_token(mock_refresh_token) == "test-access-token"


@patch("workflow_test.__main__.get_refresh_token", return_value="test-refresh-token")
@patch("workflow_test.__main__.get_access_token", return_value="test-access-token")
def test_request_api_token(mock_get_access_token, mock_get_refresh_token):
    # Load the module
    from workflow_test.__main__ import request_api_token

    result = request_api_token()
    assert result == "test-access-token"
    mock_get_refresh_token.assert_called_once()
    mock_get_access_token.assert_called_once_with("test-refresh-token")


class TestCheckApiToken(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["WORKFLOW_API_URL"] = "https://workflow-api-url.com"
        os.environ["USERNAME"] = "username"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @requests_mock.Mocker()
    @patch("logging.getLogger")
    def test_check_api_token(self, mock, mock_logger):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import check_api_token

        # Configure mocks
        mock_logger_instance = mock_logger.return_value

        mock_logger_instance.info.return_value = None
        mock.get("https://workflow-api-url.com/username/ogc-api/processes", status_code=200)

        # Check execution
        check_api_token("test-access-token")
        calls = mock_logger_instance.info.call_args_list
        assert calls[1][0][0] == "Refresh token tested successfully"


class TestWorkflowProcessing(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["GITHUB_REPO"] = "test-repo"
        os.environ["GITHUB_BRANCH"] = "main"
        os.environ["INPUTS_FILE"] = "examples/convert-url-inputs.json"
        os.environ["WORKFLOW_API_URL"] = "https://workflow-api-url.com"
        os.environ["USERNAME"] = "username"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @requests_mock.Mocker()
    @patch("logging.getLogger")
    def test_undeploy_workflow(self, mock, mock_logger):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import undeploy_workflow

        # Configure mocks
        mock.delete(
            "https://workflow-api-url.com/username/ogc-api/processes/test-convert-url",
            status_code=204,
        )
        mock_logger_instance = mock_logger.return_value
        mock_logger_instance.info.return_value = None

        # Check execution
        undeploy_workflow("valid-api-token", "test-convert-url")
        calls = mock_logger_instance.info.call_args_list
        assert calls[1][0][0] == "Workflow %s undeployed successfully"
        assert calls[1][0][1] == "test-convert-url"

    @requests_mock.Mocker()
    @patch("logging.getLogger")
    def test_deploy_workflow_url(self, mock, mock_logger):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import deploy_workflow

        # Configure mocks
        mock.post("https://workflow-api-url.com/username/ogc-api/processes", status_code=201)
        mock_logger_instance = mock_logger.return_value
        mock_logger_instance.info.return_value = None

        # Check execution
        deploy_workflow(
            "valid-api-token",
            "test-convert-url",
            "https://raw.githubusercontent.com/test-repo/main/examples/convert-url-app.cwl",
        )
        calls = mock_logger_instance.info.call_args_list
        assert calls[1][0][0] == "Workflow %s deployed successfully"
        assert calls[1][0][1] == "test-convert-url"

    @requests_mock.Mocker()
    @patch("logging.getLogger")
    def test_deploy_workflow_file(self, mock, mock_logger):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import deploy_workflow

        # Configure mocks
        mock.post("https://workflow-api-url.com/username/ogc-api/processes", status_code=201)
        mock_logger_instance = mock_logger.return_value
        mock_logger_instance.info.return_value = None

        # Check execution
        deploy_workflow("valid-api-token", "test-convert-url", "examples/convert-url-app.cwl")
        calls = mock_logger_instance.info.call_args_list
        assert calls[1][0][0] == "Workflow %s deployed successfully"
        assert calls[1][0][1] == "test-convert-url"

    @requests_mock.Mocker()
    @patch("logging.getLogger")
    def test_check_deployment_status(self, mock, mock_logger):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import check_deployment_status

        # Configure mocks
        test_url = "https://workflow-api-url.com/username/ogc-api/processes/test-convert-url"
        mock.get(
            test_url,
            status_code=200,
            json=lambda request, context: {
                "links": [{"title": "Execute End Point", "href": f"{test_url}/execution"}]
            },
        )
        mock_logger_instance = mock_logger.return_value
        mock_logger_instance.info.return_value = None

        # Check execution
        check_deployment_status("valid-api-token", "test-convert-url")
        calls = mock_logger_instance.info.call_args_list
        assert calls[1][0][0] == "Workflow %s is available"
        assert calls[1][0][1] == "test-convert-url"

    @requests_mock.Mocker()
    @patch("workflow_test.__main__.load_inputs", return_value={"inputs": {"input": "test"}})
    def test_execute_workflow(self, mock, mock_load_inputs):
        # Reload the module to ensure it reads the new environment variables

        from workflow_test.__main__ import execute_workflow

        # Configure mocks
        test_url = (
            "https://workflow-api-url.com/username/ogc-api/processes/test-convert-url/execution"
        )
        mock.post(test_url, status_code=201, json=lambda request, context: {"jobID": "test_job_id"})

        # Check execution
        job_id = execute_workflow("valid-api-token", "test-convert-url")
        assert job_id == "test_job_id"

    @requests_mock.Mocker()
    def test_monitor_workflow(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import monitor_workflow

        # Configure mocks
        test_url = "https://workflow-api-url.com/username/ogc-api/jobs/test_job_id"
        mock.get(
            test_url,
            status_code=200,
            json=lambda request, context: {
                "status": "successful",
                "links": [{"title": "Result location", "href": "results_link"}],
            },
        )

        results_link = monitor_workflow("valid-api-token", "test_job_id")

        assert results_link == "results_link"


class TestWorkflowInputsLocal(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["INPUTS_FILE"] = "examples/convert-url-app-inputs.json"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    def test_load_inputs(self):
        pass
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import load_inputs

        inputs = load_inputs()

        with open("examples/convert-url-app-inputs.json", "r") as workflow_file:
            workflow_file = workflow_file.read()

        assert inputs == json.loads(workflow_file)


class TestWorkflowInputsRemote(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["GITHUB_REPO"] = "test-repo"
        os.environ["GITHUB_BRANCH"] = "main"
        os.environ["INPUTS_FILE"] = "examples/convert-url-app-inputs.json"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @patch("github.Github")
    def test_load_inputs(self, mockGithub):
        pass
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import load_inputs

        # Configure mocks
        mock_github_instance = mockGithub.return_value
        mock_repo = Mock()
        mock_contents = Mock()
        # To mock Github access we just load local file instead
        with open("examples/convert-url-app-inputs.json", "r") as f:
            mock_contents.decoded_content = f.read()
            mock_repo.get_contents.return_value = mock_contents
        mock_github_instance.get_repo.return_value = mock_repo

        inputs = load_inputs()

        with open("examples/convert-url-app-inputs.json", "r") as workflow_file:
            workflow_file = workflow_file.read()

        assert inputs == json.loads(workflow_file)


class TestWorkflowOutputs(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["USERNAME"] = "username"
        os.environ["RESOURCE_CATALOGUE_API_URL"] = "https://resource-catalogue-api.com/rc"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @requests_mock.Mocker()
    @patch("workflow_test.__main__.client", return_value=None)
    def test_check_outputs_s3(self, mock, mock_boto3_client):
        # Only used for debug, not unit tested
        pass
        # Import the module to ensure it reads the new environment variables
        # from workflow_test.__main__ import check_outputs_in_s3

        # # Configure mocks
        # test_url = "https://workflow-api-url.com/username/ogc-api/jobs/test_job_id/results"
        # mock.get(test_url, status_code=200, json=lambda request, context: {"links":
        # [{"rel": "root", "href": "s3://bucket/root_link"},
        #  {"rel": "self", "href": "s3://bucket/self_link"},
        #  {"rel": "item", "href": "s3://bucket/item_link"},]})
        # mock_s3_client = mock_boto3_client.return_value
        # #mock_s3_client.get_object.return_value = None

        # check_outputs_in_s3("valid-api-token", "https://workflow-api-url.com/username/ogc-api/jobs/test_job_id/results")

    @requests_mock.Mocker()
    def test_get_asset_s3(self, mock):
        # Only used for debug, not unit tested
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import get_asset_from_s3

        # item_body = get_asset_from_s3()

        # assert item_body

    @requests_mock.Mocker()
    def test_get_asset_rc(self, mock):
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import get_asset_from_rc

        # Configure mocks
        test_url = "https://resource-catalogue-api.com/rc/catalogs/user-datasets/username/processing-results/cat_1234567/collections/col_1234567/items"
        mock.get(
            test_url,
            status_code=200,
            json=lambda request, context: {
                "features": [
                    {"id": "1xxxx", "title": "test_item_1"},
                    {"id": "2xxx", "title": "test_item_2"},
                    {"id": "3ccc", "title": "test_item_3"},
                ]
            },
        )

        item = get_asset_from_rc("valid-api-token", {"id": "1234567"})

        assert item == {"id": "1xxxx", "title": "test_item_1"}

    @requests_mock.Mocker()
    @patch("workflow_test.__main__.logger")
    @patch(
        "workflow_test.__main__.get_asset_from_rc",
        return_value={"id": "1xxxx", "title": "test_item_1"},
    )
    def test_check_s3_access_token(self, mock, mock_get_asset_from_rc, mock_logger):
        # Import the module to ensure it reads the new environment variables
        from workflow_test.__main__ import check_s3_access_token

        # Configure mocks
        test_url = "https://workflow-api-url.com/username/ogc-api/jobs/test_job_id/results"
        mock.get(test_url, status_code=200, json=lambda request, context: {"id": "1234567"})
        mock_logger.info.return_value = "testing"

        check_s3_access_token(
            "valid-api-token",
            "https://workflow-api-url.com/username/ogc-api/jobs/test_job_id/results",
        )

        mock_get_asset_from_rc.assert_called_once_with("valid-api-token", {"id": "1234567"})

        calls = mock_logger.info.call_args_list
        assert calls[1][0][0] == "S3 access token checked successfully"
