import json
import logging
from json import JSONDecodeError

import botocore
import requests

from .exceptions import AccessTokenException, WorkflowResultsException

logger = logging.getLogger(__name__)


class EODHPClient:
    def __init__(
        self,
        auth_url: str,
        rc_url: str,
        username: str,
        password: str,
        client_id: str,
        client_secret: str,
        refresh_token=None,
        api_token=None,
    ):
        self.auth_url = auth_url
        self.rc_url = rc_url
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token if refresh_token else None
        self.api_token = api_token if api_token else None

    def _get_refresh_token(self, debug: bool = False) -> str:
        """Get the refresh token"""
        response = requests.post(
            self.auth_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password,
                "grant_type": "password",
            },
        )
        if response.ok:
            if debug:
                logger.debug("Refresh token : %s", response.json()["refresh_token"])
            return response.json()["refresh_token"]
        else:
            try:
                error_response = response.json()
            except JSONDecodeError:
                error_response = response.text
            logger.error("Failed to get offline refresh token: %s", error_response)
            raise AccessTokenException("Failed to get offline refresh token")

    def _get_access_token(self, debug: bool = False) -> str:
        """Get the access token from the refresh token"""
        response = requests.post(
            self.auth_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
                "scope": "offline_access",
            },
        )
        if response.ok:
            if debug:
                logger.debug("Access token : %s", response.json()["access_token"])
            return response.json()["access_token"]
        else:
            try:
                error_response = response.json()
            except JSONDecodeError:
                error_response = response.text
            logger.error("Failed to get user access token: %s", error_response)
            raise AccessTokenException("Failed to get user access token")

    def request_api_token(self, debug):
        """Request the API token"""
        logger.info("Requesting API token")
        self.refresh_token = self._get_refresh_token(debug)
        api_token = self._get_access_token(debug)
        self.api_token = api_token
        logger.info("API token received")
        return api_token

    def set_client(self, client):
        """Create a boto3 client"""
        self.client = client

    def get_item_from_s3(self, collection: dict) -> dict:
        """Get the first item from S3 (DEBUG ONLY)"""
        # Identify item
        links = collection.get("links")
        for link in links:
            if link.get("rel") == "item":
                href = link.get("href")
                if href.startswith("s3://"):
                    split_href = href.split("/")
                    bucket = split_href[2]
                    key = "/".join(split_href[3:])
                    try:
                        # Load item from S3
                        print(self.client)
                        item = self.client.get_object(Bucket=bucket, Key=key)
                        print(item)
                        logger.info("S3 key found: %s", key)
                        item_body = json.loads(item["Body"].read())
                        return item_body
                    except botocore.exceptions.ClientError as err:
                        print("here")
                        if err.response["Error"]["Code"] == "NoSuchKey":
                            # File key does not exist
                            logger.error("S3 key not found: %s", key)
                            raise err
                        else:
                            logger.error("Failed to find key %s in bucket", key)
                            raise err

    def get_item_from_rc(self, collection: dict, debug: bool = None) -> dict:
        """Get the first item from the Resource Catalogue"""
        logger.info("Identifying item from Resource Catalogue")

        id = collection.get("id")
        catalog_id = f"cat_{id}"
        collection_id = f"col_{id}"

        # Get resulting collection from resource catalogue
        items_url = (
            f"{self.rc_url}/catalogs/user-datasets/{self.username}/processing-results/"
            f"{catalog_id}/collections/{collection_id}/items"
        )
        logger.info(f"Searching for item in {items_url}")
        items_response = requests.get(
            items_url, headers={"Authorization": f"Bearer {self.api_token}"}
        )
        if items_response.status_code != 200:
            logger.error("Failed to get results from %s", items_url)
            try:
                logger.error(items_response.json())
                raise WorkflowResultsException("Failed to get workflow results")
            except JSONDecodeError as err:
                logger.error(items_response.text)
                logger.error("Failed to get results from Resource Catalogue")
                raise WorkflowResultsException("Failed to get workflow results") from err
        items = items_response.json().get("features")
        # Return first item
        return items[0]

    def get_result_collection(self, results_link: str):
        """Get the result collection"""
        logger.info("Getting result collection")

        # Using results links, identify an asset href
        collection_response = requests.get(
            results_link,
            headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
        )
        if collection_response.status_code != 200:
            logger.error("Failed to get results from %s", results_link)
            try:
                logger.error(collection_response.json())
            except JSONDecodeError:
                logger.error(collection_response.text)
            raise WorkflowResultsException("Failed to get workflow results")
        try:
            collection = collection_response.json()
        except JSONDecodeError as err:
            logger.error("Failed to decode JSON")
            logger.error("Reponse text is:")
            logger.error(collection_response.text)
            raise err
        return collection

    def check_s3_access_token(self, results_link: str, debug: bool = False):
        """Check the S3 access token is valid"""
        logger.info("Checking S3 access token")

        # Get resulting collection
        collection = self.get_result_collection(results_link)

        # Identify item
        if debug:
            item_body = self.get_item_from_s3(collection)
        else:
            item_body = self.get_item_from_rc(collection)

        # Identify asset href
        if "assets" in item_body:
            # Check all assets are available for download
            for key, value in item_body["assets"].items():
                if "href" in value:
                    asset_href = value["href"]
                    response = requests.get(
                        asset_href, headers={"Authorization": f"Bearer {self.api_token}"}
                    )
                    if response.status_code == 200:
                        logger.info("Asset: %s available for download from: %s", key, asset_href)
                    else:
                        logger.error("Failed to download asset: %s from %s", key, asset_href)
                        try:
                            logger.error(response.json())
                        except JSONDecodeError:
                            logger.error(response.text)
                        raise WorkflowResultsException("Failed to download asset")

        logger.info("S3 access token checked successfully")

    def check_outputs_in_s3(self, results_link: str):
        """Check the outputs are available in S3 (DEBUG ONLY)"""
        logger.info("Checking outputs found at %s", results_link)

        # Get resulting collection
        collection = self.get_result_collection(results_link)

        # Check collection links are present in S3
        links = collection.get("links")
        links_to_check = ["root", "self", "item"]
        for link in links:
            if link.get("rel") in links_to_check:
                href = link.get("href")
                if href.startswith("s3://"):
                    split_href = href.split("/")
                    bucket = split_href[2]
                    key = "/".join(split_href[3:])
                    try:
                        self.client.get_object(Bucket=bucket, Key=key)
                        logger.info("S3 key found: %s", key)
                    except botocore.exceptions.ClientError as err:
                        if err.response["Error"]["Code"] == "NoSuchKey":
                            logger.error("S3 key not found: %s", key)
                            raise err
                        else:
                            logger.error("Failed to find key %s in bucket", key)
                            raise err
        logger.info("Outputs checked successfully")
