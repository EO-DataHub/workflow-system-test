import json
import logging
import time
from json import JSONDecodeError

import botocore
import requests

from .exceptions import WorkflowResultsException

logger = logging.getLogger(__name__)


class EODHPClient:
    def __init__(
        self,
        rc_url: str,
        user_catalog_prefix: str,
        username: str,
        api_token=None,
    ):
        self.rc_url = rc_url
        self.user_catalog_prefix = user_catalog_prefix
        self.username = username
        self.api_token = api_token

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

    def get_item_from_rc(self, workflow_id: str, collection: dict, debug: bool = None) -> dict:
        """Get the first item from the Resource Catalogue"""
        logger.info("Identifying item from Resource Catalogue")

        # Get collection_url
        links = collection.get("links", [])

        # TODO: extract catalog path from the root catalog url
        if links:
            for link in links:
                if link.get("rel") == "root":
                    root_url = link.get("href")
                    logger.info("Found root link: %s", root_url)
                    break
        else:
            raise WorkflowResultsException("No links found in collection")

        catalog_id = "catalog"
        collection_id = collection.get("id")
        if collection_id is None:
            logger.error("Results Collection ID is None")
            raise WorkflowResultsException("Results Collection ID is None")

        # Get resulting collection from resource catalogue
        items_url = (
            f"{self.rc_url}/catalogs/{self.user_catalog_prefix}/catalogs/{self.username}/catalogs/processing-results"
            f"/catalogs/{workflow_id}/catalogs/{catalog_id}/collections/{collection_id}/items"
        )
        logger.info("Searching for item in %s", items_url)
        items_response = requests.get(
            items_url, headers={"Authorization": f"Bearer {self.api_token}"}
        )
        count = 0
        while items_response.status_code == 404 and count < 5:
            logger.info("Item not found, retrying in 30 seconds")
            time.sleep(30)
            items_response = requests.get(
                items_url, headers={"Authorization": f"Bearer {self.api_token}"}
            )
            count += 1
        if items_response.status_code != 200:
            logger.error("Failed to get results from %s", items_url)
            try:
                response = items_response.json()
                logger.error("Response is %s", response)
            except JSONDecodeError:
                response = items_response.text
                logger.error("Response is %s", response)
            raise WorkflowResultsException("Failed to get workflow results")
        try:
            items_response_json = items_response.json()
        except JSONDecodeError as err:
            logger.error("Failed to decode JSON in catalogue response")
            logger.error("Response text is:")
            logger.error(items_response.text)
            raise WorkflowResultsException("Failed to get JSON from Resource Catalogue") from err
        if len(items_response_json.get("features", [])) == 0:
            logger.error("No items found in the collection yet, retrying in 30 seconds")
            time.sleep(30)
            items_response = requests.get(
                items_url, headers={"Authorization": f"Bearer {self.api_token}"}
            )
            if items_response.status_code != 200:
                logger.error("Failed to get items from %s", items_url)
                try:
                    response = items_response.json()
                    logger.error("Response is %s", response)
                except JSONDecodeError:
                    response = items_response.text
                    logger.error("Response is %s", response)
                raise WorkflowResultsException("Failed to get workflow results on second attempt")
            try:
                items_response_json = items_response.json()
            except JSONDecodeError as err:
                logger.error("Failed to decode JSON in catalogue response")
                logger.error("Response text is:")
                logger.error(items_response.text)
                raise WorkflowResultsException(
                    "Failed to get JSON from Resource Catalogue"
                ) from err
            if len(items_response_json.get("features", [])) == 0:
                logger.error("No items found in the collection")
                raise WorkflowResultsException(
                    "No items found in the collection, after second attempt"
                )
        items = items_response_json.get("features")
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

    def check_s3_access_token(self, workflow_id: str, results_link: str, debug: bool = False):
        """Check the S3 access token is valid"""
        logger.info("Checking S3 access token")

        # Get resulting collection
        collection = self.get_result_collection(results_link)

        # Identify item
        if debug:
            item_body = self.get_item_from_s3(collection)
        else:
            item_body = self.get_item_from_rc(workflow_id, collection)

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
