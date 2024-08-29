import importlib
import os
import unittest
from unittest.mock import Mock, patch

import requests_mock


class TestWorkflowLocal(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["WORKFLOW_FILE"] = "examples/test-convert-url.cwl"

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
        os.environ["WORKFLOW_FILE"] = "examples/test-convert-url.cwl"
        # Reload the module to ensure it reads the new environment variables
        from workflow_test import __main__

        importlib.reload(__main__)
        from workflow_test.__main__ import generate_workflow_address

        assert generate_workflow_address() == "examples/test-convert-url.cwl"


class TestWorkflowRemote(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["GITHUB_REPO"] = "test-repo"
        os.environ["GITHUB_BRANCH"] = "main"
        os.environ["WORKFLOW_FILE"] = "examples/test-convert-url.cwl"

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

        # configure mocks
        mock_github_instance = mockGithub.return_value
        mock_repo = Mock()
        mock_contents = Mock()
        # To mock Github access we just load local file instead
        with open("examples/test-convert-url.cwl", "r") as f:
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
            == "https://raw.githubusercontent.com/test-repo/main/examples/test-convert-url.cwl"
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

        # configure mocks
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

        # configure mocks
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

        # configure mocks
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
        os.environ["INPUTS_FILE"] = "examples/test-convert-url-inputs.json"
        os.environ["WORKFLOW_API_URL"] = "https://workflow-api-url.com"
        os.environ["USERNAME"] = "username"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @requests_mock.Mocker()
    def test_undeploy_workflow(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import undeploy_workflow

        # undeploy_workflow("valid-api-token", "workflow_id")

    @requests_mock.Mocker()
    def test_deploy_workflow_url(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import deploy_workflow

        # deploy_workflow("valid-api-token", "workflow_location")

    @requests_mock.Mocker()
    def test_deploy_workflow_file(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import deploy_workflow

        # deploy_workflow("valid-api-token", "workflow_location")

    @requests_mock.Mocker()
    def test_check_deployment_status(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import check_deployment_status

        # check_deployment_status("valid-api-token", "workflow_id")

    @requests_mock.Mocker()
    def test_execute_workflow(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import execute_workflow

        # job_id = execute_workflow("valid-api-token", "workflow_id")

        # assert job_id

    @requests_mock.Mocker()
    def test_monitor_workflow(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import monitor_workflow

        # results_link = monitor_workflow("valid-api-token", "job_id")

        # assert results_link


class TestWorkflowInputsLocal(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["INPUTS_FILE"] = "examples/test-convert-url-inputs.json"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @requests_mock.Mocker()
    def test_load_inputs(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import load_inputs

        # inputs = load_inputs()

        # assert inputs


class TestWorkflowInputsRemote(unittest.TestCase):
    def setUp(self):
        # Set environment variables
        self.original_environ = os.environ.copy()
        os.environ.clear()
        os.environ["GITHUB_REPO"] = "test-repo"
        os.environ["GITHUB_BRANCH"] = "main"
        os.environ["INPUTS_FILE"] = "examples/test-convert-url-inputs.json"

    def tearDown(self):
        # Unset environment variables
        os.environ.clear()
        os.environ.update(self.original_environ)

    @requests_mock.Mocker()
    def test_load_inputs(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import load_inputs

        # inputs = load_inputs()

        # assert inputs


class TestWorkflowOutputs(unittest.TestCase):
    @requests_mock.Mocker()
    def test_check_outputs_s3(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import check_outputs_in_s3

        # check_outputs_in_s3("valid-api-token", "results_link")

    @requests_mock.Mocker()
    def test_get_asset_s3(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import get_asset_from_s3

        # item_body = get_asset_from_s3()

        # assert item_body

    @requests_mock.Mocker()
    def test_get_asset_rc(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import get_asset_from_rc

        # get_asset_from_rc("valid-api-token", {"id": "collection_id"})

    @requests_mock.Mocker()
    def test_check_s3_access_token(self, mock):
        pass
        # Reload the module to ensure it reads the new environment variables
        # from workflow_test import __main__

        # importlib.reload(__main__)
        # from workflow_test.__main__ import check_s3_access_token

        # check_s3_access_token("valid-api-token", "results_link")
