import json
import logging
import os
import sys
import time
from distutils.util import strtobool
from json import JSONDecodeError

import boto3
import requests
import yaml
from github import Github

# Set DEBUG environment variable
DEBUG = strtobool(os.getenv("DEBUG", "false"))

# create formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# set the time converter to UTC
formatter.converter = time.gmtime

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)

# Apply the custom time formatter to all handlers
for handler in logging.getLogger().handlers:
    handler.setFormatter(formatter)

logger = logging.getLogger(__name__)  # Add this line to define the logger


# Set environment variables
# Login details
USERNAME = os.getenv("USERNAME", None)
PASSWORD = os.getenv("PASSWORD", None)

# API details
AUTH_TOKEN_API_URL = os.getenv("AUTH_TOKEN_API_URL", None)
WORKFLOW_API_URL = os.getenv("WORKFLOW_API_URL", None)
RESOURCE_CATALOGUE_API_URL = os.getenv("RESOURCE_CATALOGUE_API_URL", None)

# API credentials
CLIENT_ID = os.getenv("CLIENT_ID", None)
CLIENT_SECRET = os.getenv("CLIENT_SECRET", None)

# Workflow location details
GITHUB_REPO = os.getenv("GITHUB_REPO", None)
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", None)
WORKFLOW_FILE = os.getenv("WORKFLOW_FILE", None)
INPUTS_FILE = os.getenv("INPUTS_FILE", None)

# Set results timeout
MONITOR_TIMEOUT = os.getenv(
    "MONITOR_TIMEOUT", 270
)  # Under 5 minutes as token timesout after 5 minutes
BOOT_TIMEOUT = os.getenv("BOOT_TIMEOUT", 420)  # 7 minutes

# Set S3 client
if DEBUG and os.getenv("AWS_ACCESS_KEY_ID", None) and os.getenv("AWS_SECRET_ACCESS_KEY", None):
    client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
else:
    client = boto3.client("s3")

# Initialise Github client
if GITHUB_REPO:
    g = Github()


def get_workflow_id() -> str:
    # Code to read workflow_id from CWL
    logger.info("Getting workflow ID")
    if GITHUB_REPO:
        repo = g.get_repo(GITHUB_REPO)
        raw_file = repo.get_contents(WORKFLOW_FILE, ref=GITHUB_BRANCH)
        workflow_file = raw_file.decoded_content
        cwl_dict = yaml.safe_load(workflow_file)
    else:
        with open(WORKFLOW_FILE, "r") as workflow_file:
            cwl_dict = yaml.safe_load(workflow_file)
    workflow_id = cwl_dict.get("$graph")[0].get("id")
    logger.info("Workflow ID retrieved: %s", workflow_id)
    return workflow_id


def generate_workflow_address() -> str:
    logger.info("Generating workflow address")
    if GITHUB_REPO:
        workflow_address = (
            f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{WORKFLOW_FILE}"
        )
    else:
        workflow_address = WORKFLOW_FILE
    logger.info("Workflow address generated: %s", workflow_address)
    return workflow_address


def get_refresh_token() -> str:
    response = requests.post(
        AUTH_TOKEN_API_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": USERNAME,
            "password": PASSWORD,
            "grant_type": "password",
            # "scope": "offline_access",
        },
    )
    if response.ok:
        if DEBUG:
            logger.debug("Refresh token : %s", response.json()["refresh_token"])
        return response.json()["refresh_token"]
    else:
        try:
            error_response = response.json()
        except JSONDecodeError:
            error_response = response.text
        logger.error("Failed to get offline refresh token: %s", error_response)
        sys.exit(1)


def get_access_token(refresh_token: str) -> str:
    response = requests.post(
        AUTH_TOKEN_API_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "offline_access",
        },
    )
    if response.ok:
        if DEBUG:
            logger.debug("Access token : %s", response.json()["access_token"])
        return response.json()["access_token"]
    else:
        try:
            error_response = response.json()
        except JSONDecodeError:
            error_response = response.text
        logger.error("Failed to get user access token: %s", error_response)
        sys.exit(1)


def request_api_token():
    logger.info("Requesting API token")
    refresh_token = get_refresh_token()
    api_token = get_access_token(refresh_token)
    logger.info("API token received")
    return api_token


def check_api_token(api_token: str):
    logger.info("Testing refresh token")
    response = requests.get(
        f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/processes",
        headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
    )
    if response.status_code == 200:
        logger.info("Refresh token tested successfully")
    else:
        try:
            error_response = response.json()
        except JSONDecodeError:
            error_response = response.text
        logger.error("Refresh token failed: %s", error_response)
        sys.exit(1)


def check_ades_status():
    logger.info("Checking ADES status")
    response = requests.get(WORKFLOW_API_URL)
    if response.status_code == 200:
        logger.info("ADES is running")
        return
    logger.info("Waiting for ADES to start up")
    start_time = time.time()
    final_timeout = start_time + BOOT_TIMEOUT
    logger.info(f"Waiting {BOOT_TIMEOUT} seconds for ADES to start")
    while time.time() < final_timeout:
        logger.info("Waiting for ADES to start")
        time.sleep(5)
        response = requests.get(WORKFLOW_API_URL)
        if response.status_code == 200:
            logger.info("ADES is running")
            break
    logger.error("ADES start up reached timeout, ending test")
    sys.exit(1)


def undeploy_workflow(api_token: str, workflow_id: str):
    logger.info("Undeploying workflow")
    response = requests.delete(
        f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/processes/{workflow_id}",
        headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
    )
    if response.status_code == 204:
        logger.info("Workflow %s undeployed successfully", workflow_id)
    elif response.status_code == 403:
        logger.info("Workflow %s not found, continuing", workflow_id)
    else:
        logger.error("Failed to undeploy workflow %s: %s", workflow_id, response.json())


def deploy_workflow(api_token: str, workflow_id: str, workflow_location: str):
    if workflow_location.startswith("https://"):
        logger.info("Deploying workflow from URL")
        response = requests.post(
            f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/processes",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "executionUnit": {"href": workflow_location, "type": "application/cwl"},
            },
        )
    else:
        logger.info("Deploying workflow from local file")
        with open(workflow_location, "r") as workflow_file:
            workflow_file = workflow_file.read()
        response = requests.post(
            f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/processes",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/cwl+yaml",
            },
            data=workflow_file,
        )
    if response.status_code == 201:
        logger.info("Workflow %s deployed successfully", workflow_id)
    elif response.status_code == 409:
        logger.warning("Workflow %s already deployed, it should have been deleted", workflow_id)
    else:
        logger.error("Failed to deploy workflow %s : %s", workflow_id, response.text)
        sys.exit(1)


def check_deployment_status(api_token: str, workflow_id: str):
    logger.info("Checking deployment status")
    response = requests.get(
        f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/processes/{workflow_id}",
        headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
    )
    if response.status_code == 200:
        logger.info("Workflow %s is available", workflow_id)
        # Check deployment execute link is correct
        for link in response.json().get("links"):
            if link["title"] == "Execute End Point":
                if (
                    link["href"]
                    != f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/processes/{workflow_id}/execution"
                ):
                    logger.error("Deployment execute link is incorrect")
                    sys.exit(1)
    elif response.status_code == 404:
        logger.error("Workflow %s not deployed", workflow_id)
        sys.exit(1)
    else:
        logger.error(
            "Failed to check deployment status for workflow %s : %s", workflow_id, response.json()
        )


def load_inputs() -> dict:
    logger.info("Loading inputs")
    if GITHUB_REPO:
        repo = g.get_repo(GITHUB_REPO)
        raw_file = repo.get_contents(INPUTS_FILE, ref=GITHUB_BRANCH)
        workflow_file = raw_file.decoded_content
    else:
        with open(INPUTS_FILE, "r") as workflow_file:
            workflow_file = workflow_file.read()
    try:
        inputs = json.loads(workflow_file)
        logger.info("Inputs loaded")
    except JSONDecodeError:
        logger.error("Failed to decode JSON")
        logger.error("Reponse text is:")
        logger.error(workflow_file)
        sys.exit(1)
    return inputs


def execute_workflow(api_token: str, workflow_id: str) -> str:
    logger.info("Preparing to execute workflow")
    inputs = load_inputs()
    inputs["inputs"].update({"workspace": USERNAME})
    logger.info("Executing workflow")
    response = requests.post(
        f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/processes/{workflow_id}/execution",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "prefer": "respond-async",
        },
        json=inputs,
    )
    if response.status_code == 201:
        job_id = response.json().get("jobID")
        logger.info("Workflow: %s executed under job: %s", workflow_id, job_id)
    else:
        logger.error("Failed to execute workflow: %s", response.json())
        sys.exit(1)
    return job_id


def monitor_workflow(api_token: str, job_id: str) -> str:
    logger.info("Monitoring workflow")
    response = requests.get(
        f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/jobs/{job_id}",
        headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
    )
    start_time = time.time()
    final_timeout = start_time + MONITOR_TIMEOUT
    while time.time() < final_timeout:
        if response.status_code == 200:
            if response.json().get("status") == "successful":
                logger.info("Workflow completed, job id: %s", job_id)
                links = response.json().get("links")
                for link in links:
                    if link.get("title") == "Result location":
                        results_link = link.get("href")
                        return results_link
                logger.error("Failed to find results link")
                sys.exit(1)
            elif response.json().get("status") == "failed":
                logger.error("Workflow failed, job id: %s", job_id)
                logger.error(response.json().get("message"))
                sys.exit(1)
            else:
                logger.info("Workflow still running, message: %s", response.json().get("message"))
                time.sleep(5)
                response = requests.get(
                    f"{WORKFLOW_API_URL}/{USERNAME}/ogc-api/jobs/{job_id}",
                    headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
                )
        else:
            try:
                logger.error("Failed to monitor job %s: %s", job_id, response.json())
            except JSONDecodeError:
                logger.error("Failed to monitor job %s: %s", job_id, response.text)
            sys.exit(1)

    logger.error("Workflow timed out, job id: %s", job_id)
    sys.exit(1)


def check_outputs_in_s3(api_token: str, results_link: str):
    logger.info("Checking outputs found at %s", results_link)
    # Get resulting collection
    collection_response = requests.get(
        results_link, headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"}
    )
    if collection_response.status_code != 200:
        logger.error("Failed to get results from %", results_link)
        try:
            logger.error(collection_response.json())
        except JSONDecodeError:
            logger.error(collection_response.text)
    collection = collection_response.json()
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
                    client.get_object(Bucket=bucket, Key=key)
                    logger.info("S3 key found: %s", key)
                except client.exceptions.NoSuchKey:
                    logger.error("S3 key not found: %s", key)
                    sys.exit(1)
    logger.info("Outputs checked")


def get_asset_from_s3(collection: dict) -> dict:
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
                    item = client.get_object(Bucket=bucket, Key=key)
                    logger.info("S3 key found: %s", key)
                    item_body = json.loads(item["Body"].read())
                    return item_body
                except client.exceptions.NoSuchKey:
                    logger.error("S3 key not found: %s", key)
                    sys.exit(1)


def get_asset_from_rc(api_token: str, collection: dict) -> dict:
    logger.info("Identifying asset from Resource Catalogue")
    id = collection.get("id")
    catalog_id = f"cat_{id}"
    collection_id = f"col_{id}"
    # Get resulting collection from resource catalogue
    items_url = (
        f"{RESOURCE_CATALOGUE_API_URL}/catalogs/user-datasets/{USERNAME}/processing-results/"
        f"{catalog_id}/collections/{collection_id}/items"
    )
    logger.info(f"Searching for assets in {items_url}")
    items_response = requests.get(items_url, headers={"Authorization": f"Bearer {api_token}"})
    if items_response.status_code != 200:
        logger.error("Failed to get results from %s", items_url)
        try:
            logger.error(items_response.json())
        except JSONDecodeError:
            logger.error(items_response.text)
            sys.exit(1)
    items = items_response.json().get("features")
    # Return first item
    return items[0]


def check_s3_access_token(api_token: str, results_link: str):
    logger.info("Checking S3 access token")
    # Using results links, identify an asset href
    collection_response = requests.get(
        results_link, headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"}
    )
    if collection_response.status_code != 200:
        logger.error("Failed to get results from %s", results_link)
        try:
            logger.error(collection_response.json())
        except JSONDecodeError:
            logger.error(collection_response.text)
        sys.exit(1)
    try:
        collection = collection_response.json()
    except JSONDecodeError:
        logger.error("Failed to decode JSON")
        logger.error("Reponse text is:")
        logger.error(collection_response.text)
        sys.exit(1)
    # Identify item
    item_body = get_asset_from_rc(api_token, collection)
    # Identify asset href
    if "assets" in item_body:
        # Check all assets are available for download
        for key, value in item_body["assets"].items():
            if "href" in value:
                asset_href = value["href"]
                response = requests.get(
                    asset_href, headers={"Authorization": f"Bearer {api_token}"}
                )
                if response.status_code == 200:
                    logger.info("Asset: %s available for download from: %s", key, asset_href)
                else:
                    logger.error("Failed to download asset: %s from %s", key, asset_href)
                    logger.error(response.json())
                    sys.exit(1)

    logger.info("S3 access token checked successfully")


if __name__ == "__main__":
    # Check ades is running
    check_ades_status()
    # Generate API token
    api_token = request_api_token()
    # Test API token access
    check_api_token(api_token)
    # Generate workflow address (either URL or local file)
    workflow_location = generate_workflow_address()
    # Identify workflow ID
    workflow_id = get_workflow_id()
    # Undeploy workflow if it exists
    undeploy_workflow(api_token, workflow_id)
    # Need to wait after undeployment for a few seconds before workflow is available for deployment
    time.sleep(5)
    # Deploy workflow
    deploy_workflow(api_token, workflow_id, workflow_location)
    # Check deployment status
    check_deployment_status(api_token, workflow_id)
    # Need to wait after deployment for a few seconds before workflow is available for execution
    time.sleep(5)
    # Execute workflow
    job_id = execute_workflow(api_token, workflow_id)
    # Monitor workflow execution for success or failure
    results_link = monitor_workflow(api_token, job_id)
    if DEBUG:
        # Check in S3 to confirm all outputs are present (debug only)
        check_outputs_in_s3(api_token, results_link)
    # Check token allows outputs to be downloaded
    check_s3_access_token(api_token, results_link)
    logger.info("Test is successful")
