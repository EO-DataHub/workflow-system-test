import io
import unittest
from unittest.mock import Mock, patch

from system_tests.eodhp import EODHPClient


class TestEODHPClient(unittest.TestCase):
    def test_init(self) -> None:
        eodhp_client = EODHPClient("https://test-rc-url", "user-catalogue-prefix", "username", "api-token")

        assert eodhp_client.rc_url == "https://test-rc-url"
        assert eodhp_client.user_catalog_prefix == "user-catalogue-prefix"
        assert eodhp_client.username == "username"
        assert eodhp_client.api_token == "api-token"

    def test_get_item_from_s3(self) -> None:
        eodhp_client = EODHPClient("https://test-rc-url", "user-catalogue-prefix", "username", "api-token")

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

        assert item == {"id": "test_item", "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link"}]}

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    def test_get_item_from_rc(self, MockRequests: Mock) -> None:
        eodhp_client = EODHPClient("https://test-rc-url", "user-catalogue-prefix", "username", "api-token")
        workflow_id = "test-workflow"

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

        collection = {
            "id": "test_collection_id",
            "links": [{"rel": "item", "href": "s3://test-bucket/test-key"}],
        }

        item = eodhp_client.get_item_from_rc(workflow_id, collection)

        expected_url = (
            "https://test-rc-url/catalogs/user-catalogue-prefix/catalogs/username/catalogs/"
            f"processing-results/catalogs/{workflow_id}/catalogs/catalog/collections/test_collection_id/items"
        )
        MockRequests.get.assert_called_once_with(expected_url, headers={"Authorization": "Bearer api-token"})

        assert item == {"id": "test_item", "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link1"}]}

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    def test_get_result_collection(self, MockRequests: Mock) -> None:
        eodhp_client = EODHPClient("https://test-rc-url", "user-catalogue-prefix", "username", "api-token")

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
        self, mock_logger: Mock, mock_get_item_from_rc: Mock, mock_get_result_collection: Mock, MockRequests: Mock
    ) -> None:
        eodhp_client = EODHPClient("https://test-rc-url", "user-catalogue-prefix", "username", "api-token")
        workflow_id = "test-workflow"

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

        eodhp_client.check_s3_access_token(workflow_id, "https://test-results-link")

        mock_get_item_from_rc.assert_called_once_with(
            workflow_id,
            {
                "id": "test_collection_id",
                "links": [{"rel": "item", "href": "s3://test-bucket/test-key"}],
            },
        )

        calls = mock_logger.info.call_args_list

        assert calls[1][0][0] == "Asset: %s available for download from: %s"
        assert calls[1][0][1] == "asset_1"
        assert calls[1][0][2] == "https://data-access/path/asset_link1"
        assert calls[2][0][0] == "Asset: %s available for download from: %s"
        assert calls[2][0][1] == "asset_2"
        assert calls[2][0][2] == "https://data-access/path/asset_link2"

    @patch("system_tests.eodhp.EODHPClient.get_result_collection")  # Mock the load_inputs method
    @patch("system_tests.eodhp.logger")  # Mock the logger module
    def test_check_outputs_in_s3(self, mock_logger: Mock, mock_get_result_collection: Mock) -> None:
        eodhp_client = EODHPClient("https://test-rc-url", "user-catalogue-prefix", "username", "api-token")

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
