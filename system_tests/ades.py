import logging
import time
from collections.abc import Mapping
from json import JSONDecodeError

import requests

from .cwl_loader import CWLFile
from .exceptions import (
    AccessTokenException,
    ADESTimeOutException,
    WorkflowDeploymentException,
    WorkflowExecutionException,
    WorkflowMonitorException,
)

logger = logging.getLogger(__name__)


class ADESClient:
    def __init__(
        self,
        url: str,
        workspace: str,
        api_suffix: str | None = None,
        boot_timeout: int = 270,
        monitor_timeout: int = 270,
        api_token: str | None = None,
    ) -> None:
        self.url = url
        self.workspace = workspace
        if api_suffix:
            self.user_url = f"{self.url}/{self.workspace}/{api_suffix}"
        else:
            self.user_url = f"{self.url}/{self.workspace}"
        self.boot_timeout = boot_timeout
        self.monitor_timeout = monitor_timeout
        self.api_token = api_token

    def set_api_token(self, api_token: str) -> None:
        self.api_token = api_token

    def check_status(self) -> None:
        """Check the ADES is running and available"""
        logger.info("Checking ADES status")
        response = requests.get(self.url)
        if response.status_code == 200:
            logger.info("ADES is running")
            return
        logger.info("Waiting for ADES to start up")
        start_time = time.time()
        final_timeout = start_time + self.boot_timeout
        logger.info(f"Waiting {self.boot_timeout} seconds for ADES to start")
        while time.time() < final_timeout:
            if final_timeout - time.time() < 10:
                logger.warning("Monitoring workflow, time left: %s", final_timeout - time.time())
            logger.info("Waiting for ADES to start")
            time.sleep(5)
            response = requests.get(self.url)
            if response.status_code == 200:
                logger.info("ADES is running")
                return
        logger.error("ADES start up reached timeout, ending test")
        raise ADESTimeOutException("ADES start up reached timeout")

    def check_api_token(self) -> None:
        """Check the API token is valid"""
        logger.info("Testing refresh token")
        response = requests.get(
            f"{self.user_url}/processes",
            headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
        )
        if response.status_code == 200:
            logger.info("API token tested successfully")
        else:
            try:
                error_response = response.json()
            except JSONDecodeError:
                error_response = response.text
            logger.error("Refresh token failed: %s", error_response)
            raise AccessTokenException("Refresh token failed")

    def undeploy_workflow(self, workflow_id: str) -> None:
        """Undeploy the workflow if it is already deployed"""
        logger.info("Undeploying workflow")
        response = requests.delete(
            f"{self.user_url}/processes/{workflow_id}",
            headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
        )
        if response.status_code == 204:
            logger.info("Workflow %s undeployed successfully", workflow_id)
        elif response.status_code == 403:
            logger.info("Workflow %s not found, continuing", workflow_id)
        else:
            logger.error("Failed to undeploy workflow %s: %s", workflow_id, response.json())

    def check_deployment_status_link(self, headers: Mapping[str, str], cwl_file: CWLFile) -> None:
        # Check deployment status link is correct
        for header, value in headers.items():
            if header == "Location" and value != f"{self.user_url}/processes/{cwl_file.get_workflow_id()}":
                logger.error("Deployment status link is incorrect")
                raise WorkflowDeploymentException("Deployment status link is incorrect")

    def call_deploy_endpoint_url(self, location: str) -> requests.Response:
        response = requests.post(
            f"{self.user_url}/processes",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "executionUnit": {"href": location, "type": "application/cwl"},
            },
        )
        return response

    def call_deploy_endpoint_file(self, location: str) -> requests.Response:
        with open(location) as workflow_file:
            workflow_file = workflow_file.read()
        response = requests.post(
            f"{self.user_url}/processes",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/cwl+yaml",
            },
            data=workflow_file,
        )
        return response

    def deploy_workflow(self, cwl_file: CWLFile) -> None:
        """Deploy the workflow to the ADES"""
        if cwl_file.location.startswith("https://"):
            logger.info("Deploying workflow from URL: %s", cwl_file.location)
            response = self.call_deploy_endpoint_url(cwl_file.location)
            if response.status_code == 429:
                logger.warning(
                    "Too many requests, waiting to try again.",
                )
                time.sleep(5)
                response = self.call_deploy_endpoint_url(cwl_file.location)
        else:
            logger.info("Deploying workflow from local file")
            response = self.call_deploy_endpoint_file(cwl_file.location)
            if response.status_code == 429:
                logger.warning(
                    "Too many requests, waiting to try again.",
                )
                time.sleep(5)
                response = self.call_deploy_endpoint_file(cwl_file.location)
        if response.status_code == 201:
            logger.info("Workflow %s deployed successfully", cwl_file.get_workflow_id())
            # Check response header Location is correct
            self.check_deployment_status_link(response.headers, cwl_file)
        elif response.status_code == 409:
            logger.warning(
                "Workflow %s already deployed, it should have been deleted",
                cwl_file.get_workflow_id(),
            )
        else:
            logger.error("Failed to deploy workflow %s : %s", cwl_file.get_workflow_id(), response.text)
            raise WorkflowDeploymentException("Failed to deploy workflow")

    def check_deployment_status(self, workflow_id: str) -> None:
        """Check the deployment status of the workflow"""
        logger.info("Checking deployment status")
        response = requests.get(
            f"{self.user_url}/processes/{workflow_id}",
            headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
        )
        if response.status_code == 200:
            logger.info("Workflow %s is available", workflow_id)
            # Check deployment execute link is correct
            for link in response.json().get("links"):
                if (
                    link["title"] == "Execute End Point"
                    and link["href"] != f"{self.user_url}/processes/{workflow_id}/execution"
                ):
                    logger.error("Deployment execute link is incorrect")
                    raise WorkflowDeploymentException("Deployment execute link is incorrect")
        elif response.status_code == 404:
            logger.error("Workflow %s not deployed", workflow_id)
            raise WorkflowDeploymentException("Failed to deploy workflow")
        else:
            logger.error(
                "Failed to check deployment status for workflow %s : %s",
                workflow_id,
                response.json(),
            )
            raise WorkflowDeploymentException("Failed to check deployment status")

    def execute_workflow(self, workflow: CWLFile) -> str:
        """Execute the workflow"""
        logger.info("Preparing to execute workflow")
        inputs = workflow.get_workflow_inputs()
        inputs["inputs"].update({"workspace": self.workspace})
        logger.info("Executing workflow")
        response = requests.post(
            f"{self.user_url}/processes/{workflow.get_workflow_id()}/execution",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "prefer": "respond-async",
            },
            json=inputs,
        )
        if response.status_code == 201:
            job_id = response.json().get("jobID")
            logger.info("Workflow: %s executed under job: %s", workflow.get_workflow_id(), job_id)
        else:
            logger.error("Failed to execute workflow: %s", response.json())
            raise WorkflowExecutionException("Failed to execute workflow")
        return job_id

    def monitor_workflow(self, job_id: str) -> str:
        """Monitor the workflow execution and wait for results"""
        logger.info("Monitoring workflow")
        status_url = f"{self.user_url}/jobs/{job_id}"
        response = requests.get(
            status_url,
            headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
        )
        start_time = time.time()
        final_timeout = start_time + self.monitor_timeout
        while time.time() < final_timeout:
            if final_timeout - time.time() < 10:
                logger.warning("Monitoring workflow, time left: %s", final_timeout - time.time())
            if response.status_code == 200:
                if response.json().get("status") == "successful":
                    logger.info("Workflow completed, job id: %s", job_id)
                    links = response.json().get("links")
                    self.check_logs_access(status_url, links)
                    results_link = ""
                    for link in links:
                        if link.get("title") == "Result location":
                            results_link = link.get("href")
                            return results_link
                    logger.error("Failed to find results link")
                    raise WorkflowMonitorException("Failed to find results link")
                elif response.json().get("status") == "failed":
                    logger.error("Workflow failed, job id: %s", job_id)
                    logger.error(response.json().get("message"))
                    raise WorkflowMonitorException("Workflow failed during execution")
                else:
                    logger.info("Workflow still running, message: %s", response.json().get("message"))
                    time.sleep(5)
                    response = requests.get(
                        f"{self.user_url}/jobs/{job_id}",
                        headers={
                            "Authorization": f"Bearer {self.api_token}",
                            "Accept": "application/json",
                        },
                    )
            else:
                try:
                    logger.error("Failed to monitor job %s: %s", job_id, response.json())
                except JSONDecodeError:
                    logger.error("Failed to monitor job %s: %s", job_id, response.text)
                raise WorkflowMonitorException("Failed to monitor job")

        logger.error("Workflow timed out, job id: %s", job_id)
        raise WorkflowMonitorException("Workflow timed out")

    def monitor_workflow_failure(self, job_id: str, expected_message: str | None = None) -> str:
        """Monitor a workflow execution that is expected to fail and return its failure message"""
        logger.info("Monitoring workflow, expecting it to fail")
        final_timeout = time.time() + self.monitor_timeout
        while time.time() < final_timeout:
            response = requests.get(
                f"{self.user_url}/jobs/{job_id}",
                headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
            )
            if response.status_code != 200:
                logger.error("Failed to monitor job %s: %s", job_id, response.text)
                raise WorkflowMonitorException("Failed to monitor job")
            status = response.json().get("status")
            message = response.json().get("message") or ""
            if status == "failed":
                logger.info("Workflow failed as expected, job id: %s, message: %s", job_id, message)
                if "Traceback" in message:
                    raise WorkflowMonitorException("Failure message contains a stack trace")
                if expected_message and expected_message not in message:
                    raise WorkflowMonitorException(f"Failure message does not contain '{expected_message}'")
                return message
            if status == "successful":
                logger.error("Workflow succeeded but was expected to fail, job id: %s", job_id)
                raise WorkflowMonitorException("Workflow succeeded but was expected to fail")
            logger.info("Workflow still running, message: %s", message)
            time.sleep(5)

        logger.error("Workflow timed out, job id: %s", job_id)
        raise WorkflowMonitorException("Workflow timed out")

    def check_logs_access(self, status_url: str, links: list) -> None:
        """Check the logs are accessible"""
        logger.info("Checking logs are accessible")
        logs_link = ""
        for link in links:
            if link.get("title") == "Tool log node_stage_out.log":
                logs_link = link.get("href")
        start_time = time.time()
        final_timeout = start_time + 60  # Give 60 seconds for logs to be available
        while not logs_link and time.time() < final_timeout:
            logger.info("Waiting for logs to become available")
            response = requests.get(
                status_url,
                headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
            )
            links = response.json().get("links")
            for link in links:
                if link.get("title") == "Tool log node_stage_out.log":
                    logs_link = link.get("href")
                    break
            time.sleep(5)
        if not logs_link:
            logger.warning("Failed to find logs link")
            return
        response = requests.get(
            logs_link,
            headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
        )
        if response.status_code == 200:
            logger.info("Logs are accessible")
        else:
            try:
                logger.error("Failed to get logs at url: %s : %s", logs_link, response.json())
            except JSONDecodeError:
                logger.error("Failed to get logs at url: %s : %s", logs_link, response.text)
            raise WorkflowMonitorException("Failed to access logs")
