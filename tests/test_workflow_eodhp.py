import io
import unittest
from unittest.mock import Mock, patch

from system_tests.eodhp import EODHPClient


class TestEODHPClient(unittest.TestCase):
    def test_init(self):
        eodhp_client = EODHPClient(
            "https://test-auth-url",
            "https://test-rc-url",
            "username",
            "password",
            "client_id",
            "client_secret",
        )

        assert eodhp_client.auth_url == "https://test-auth-url"
        assert eodhp_client.rc_url == "https://test-rc-url"
        assert eodhp_client.username == "username"
        assert eodhp_client.password == "password"
        assert eodhp_client.client_id == "client_id"
        assert eodhp_client.client_secret == "client_secret"
        assert eodhp_client.api_token is None

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    def test_get_refresh_token(self, MockRequests):
        # Configure mocks
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"refresh_token": "test_refresh_token"}
        MockRequests.post.return_value = mock_response

        eodhp_client = EODHPClient(
            "https://test-auth-url",
            "https://test-rc-url",
            "username",
            "password",
            "client_id",
            "client_secret",
        )

        refresh_token = eodhp_client._get_refresh_token()

        assert refresh_token == "test_refresh_token"

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    def test_get_access_token(self, MockRequests):
        # Configure mocks
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"access_token": "test_access_token"}
        MockRequests.post.return_value = mock_response

        eodhp_client = EODHPClient(
            "https://test-auth-url",
            "https://test-rc-url",
            "username",
            "password",
            "client_id",
            "client_secret",
            "test_refresh_token",
        )

        # Check refresh token set correctly

        assert eodhp_client.refresh_token == "test_refresh_token"

        access_token = eodhp_client._get_access_token()

        assert access_token == "test_access_token"

    def test_get_item_from_s3(self):
        eodhp_client = EODHPClient(
            "https://test-auth-url",
            "https://test-rc-url",
            "username",
            "password",
            "client_id",
            "client_secret",
            "test_refresh_token",
            "test_access_token",
        )

        collection = {
            "id": "test_collection_id",
            "links": [{"rel": "item", "href": "s3://test-bucket/test-key"}],
        }
        client = Mock()
        test_item = '{"id": "test_item", "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link"}]}'
        test_item_string = io.StringIO(test_item)
        client.get_object.return_value = {"Body": test_item_string}

        eodhp_client.set_client(client)

        item = eodhp_client.get_item_from_s3(collection)

        assert item == {
            "id": "test_item",
            "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link"}],
        }

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    def test_get_item_from_rc(self, MockRequests):
        eodhp_client = EODHPClient(
            "https://test-auth-url",
            "https://test-rc-url",
            "username",
            "password",
            "client_id",
            "client_secret",
            "test_refresh_token",
            "test_access_token",
        )

        # Configure mocks
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
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
        MockRequests.get.return_value = mock_response

        collection = {
            "id": "test_collection_id",
            "links": [{"rel": "item", "href": "s3://test-bucket/test-key"}],
        }

        item = eodhp_client.get_item_from_rc(collection)

        assert item == {
            "id": "test_item",
            "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link1"}],
        }

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    def test_get_result_collection(self, MockRequests):
        eodhp_client = EODHPClient(
            "https://test-auth-url",
            "https://test-rc-url",
            "username",
            "password",
            "client_id",
            "client_secret",
            "test_refresh_token",
            "test_access_token",
        )

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_collection_id",
            "links": [{"rel": "item", "href": "s3://test-bucket/test-key"}],
        }
        MockRequests.get.return_value = mock_response

        results_link = "https://test-results-link"

        collection = eodhp_client.get_result_collection(results_link)

        assert collection == {
            "id": "test_collection_id",
            "links": [{"rel": "item", "href": "s3://test-bucket/test-key"}],
        }

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    @patch("system_tests.eodhp.EODHPClient.get_result_collection")  # Mock the load_inputs method
    @patch("system_tests.eodhp.EODHPClient.get_item_from_rc")  # Mock the load_inputs method
    @patch("system_tests.eodhp.logger")  # Mock the logger module
    def test_check_s3_access_token(
        self, mock_logger, mock_get_item_from_rc, mock_get_result_collection, MockRequests
    ):
        eodhp_client = EODHPClient(
            "https://test-auth-url",
            "https://test-rc-url",
            "username",
            "password",
            "client_id",
            "client_secret",
            "test_refresh_token",
            "test_access_token",
        )

        # Configure mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
        MockRequests.get.return_value = mock_response

        mock_get_result_collection.return_value = {
            "id": "test_collection_id",
            "links": [{"rel": "item", "href": "s3://test-bucket/test-key"}],
        }
        mock_get_item_from_rc.return_value = {
            "id": "test_item",
            "assets": {
                "asset_1": {"href": "https://data-access/path/asset_link1"},
                "asset_2": {"href": "https://data-access/path/asset_link2"},
            },
            "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link"}],
        }

        eodhp_client.check_s3_access_token("https://test-results-link")

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Asset: %s available for download from: %s"
        assert calls[1][0][1] == "asset_1"
        assert calls[1][0][2] == "https://data-access/path/asset_link1"
        assert calls[2][0][0] == "Asset: %s available for download from: %s"
        assert calls[2][0][1] == "asset_2"
        assert calls[2][0][2] == "https://data-access/path/asset_link2"

    @patch("system_tests.eodhp.EODHPClient.get_result_collection")  # Mock the load_inputs method
    @patch("system_tests.eodhp.logger")  # Mock the logger module
    def test_check_outputs_in_s3(self, mock_logger, mock_get_result_collection):
        eodhp_client = EODHPClient(
            "https://test-auth-url",
            "https://test-rc-url",
            "username",
            "password",
            "client_id",
            "client_secret",
            "test_refresh_token",
            "test_access_token",
        )

        mock_get_result_collection.return_value = {
            "id": "test_collection_id",
            "links": [
                {"rel": "item", "href": "s3://test-bucket/item"},
                {"rel": "self", "href": "s3://test-bucket/self"},
                {"rel": "root", "href": "s3://test-bucket/root"},
            ],
        }

        client = Mock()
        client.get_object.return_value = None

        eodhp_client.set_client(client)

        results_link = "https://test-results-link"

        eodhp_client.check_outputs_in_s3(results_link)

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "S3 key found: %s"
        assert calls[1][0][1] == "item"
        assert calls[2][0][0] == "S3 key found: %s"
        assert calls[2][0][1] == "self"
        assert calls[3][0][0] == "S3 key found: %s"
        assert calls[3][0][1] == "root"
