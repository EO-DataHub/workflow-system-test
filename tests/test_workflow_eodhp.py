import io
import unittest
from unittest.mock import Mock, patch

from system_tests.eodhp import EODHPClient


class TestEODHPClient(unittest.TestCase):
    def test_init(self):
        eodhp_client = EODHPClient("https://test-rc-url", "user", "username", "api-token")

        self.assertEqual("https://test-rc-url", eodhp_client.rc_url)
        self.assertEqual("username", eodhp_client.username)
        self.assertEqual("api-token", eodhp_client.api_token)

    def test_get_item_from_s3(self):
        eodhp_client = EODHPClient("https://test-rc-url", "user", "username", "api-token")

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

        self.assertEqual(
            {
                "id": "test_item",
                "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link"}],
            },
            item,
        )

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    def test_get_item_from_rc(self, MockRequests):
        eodhp_client = EODHPClient("https://test-rc-url", "user", "username", "api-token")
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
            "https://test-rc-url/catalogs/user/catalogs/username/catalogs/"
            f"processing-results/catalogs/{workflow_id}/catalogs/cat_test_collection_id/collections/col_test_collection_id/items"
        )
        MockRequests.get.assert_called_once_with(
            expected_url, headers={"Authorization": "Bearer api-token"}
        )

        self.assertEqual(
            {
                "id": "test_item",
                "links": [{"rel": "self", "href": "s3://bucket_name/path/item_link1"}],
            },
            item,
        )

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    def test_get_result_collection(self, MockRequests):
        eodhp_client = EODHPClient("https://test-rc-url", "user", "username", "api-token")

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

        self.assertEqual(
            {
                "id": "test_collection_id",
                "links": [{"rel": "item", "href": "s3://test-bucket/test-key"}],
            },
            collection,
        )

    @patch("system_tests.eodhp.requests")  # Mock the requests module
    @patch("system_tests.eodhp.EODHPClient.get_result_collection")  # Mock the load_inputs method
    @patch("system_tests.eodhp.EODHPClient.get_item_from_rc")  # Mock the load_inputs method
    @patch("system_tests.eodhp.logger")  # Mock the logger module
    def test_check_s3_access_token(
        self, mock_logger, mock_get_item_from_rc, mock_get_result_collection, MockRequests
    ):
        eodhp_client = EODHPClient("https://test-rc-url", "user", "username", "api-token")
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

        self.assertEqual("Asset: %s available for download from: %s", calls[1][0][0])
        self.assertEqual("asset_1", calls[1][0][1])
        self.assertEqual("https://data-access/path/asset_link1", calls[1][0][2])
        self.assertEqual("Asset: %s available for download from: %s", calls[2][0][0])
        self.assertEqual("asset_2", calls[2][0][1])
        self.assertEqual("https://data-access/path/asset_link2", calls[2][0][2])

    @patch("system_tests.eodhp.EODHPClient.get_result_collection")  # Mock the load_inputs method
    @patch("system_tests.eodhp.logger")  # Mock the logger module
    def test_check_outputs_in_s3(self, mock_logger, mock_get_result_collection):
        eodhp_client = EODHPClient("https://test-rc-url", "user", "username", "api-token")

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

        self.assertEqual("S3 key found: %s", calls[1][0][0])
        self.assertEqual("item", calls[1][0][1])
        self.assertEqual("S3 key found: %s", calls[2][0][0])
        self.assertEqual("self", calls[2][0][1])
        self.assertEqual("S3 key found: %s", calls[3][0][0])
        self.assertEqual("root", calls[3][0][1])
