import logging
import os
import time

import boto3
import click

from .ades import ADESClient
from .cwl_loader import FileCWLLoader, GitCWLLoader
from .eodhp import EODHPClient

# create formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# set the time converter to UTC
formatter.converter = time.gmtime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)

# Apply the custom time formatter to all handlers
for handler in logging.getLogger().handlers:
    handler.setFormatter(formatter)

logger = logging.getLogger(__name__)  # Add this line to define the logger


@click.group()
def cli():
    pass


@cli.command()
@click.argument("workflow-api-url")
@click.argument("resource-catalogue-api-url")
@click.argument("workflow-file-name")
@click.argument("inputs-file-name")
@click.option("--github-repo", "-gr", default=None, help="GitHub repository")
@click.option("--github-branch", "-gb", default=None, help="GitHub branch")
@click.option("--debug", is_flag=True, help="Toggle debug mode")
@click.option("--boot-timeout", default=420, help="Boot timeout in seconds")
@click.option("--monitor-timeout", default=270, help="Monitor timeout in seconds")
def workflow(
    workflow_api_url,
    resource_catalogue_api_url,
    workflow_file_name,
    inputs_file_name,
    github_repo,
    github_branch,
    debug,
    boot_timeout,
    monitor_timeout,
):
    logger.info("Starting workflow system test")

    # Set DEBUG logging
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialise Github client
    if github_repo:
        cwl_loader = GitCWLLoader(
            cwl_filename=workflow_file_name,
            inputs_filename=inputs_file_name,
            repo_name=github_repo,
            branch_name=github_branch,
        )
    else:
        cwl_loader = FileCWLLoader(
            cwl_filename=workflow_file_name, inputs_filename=inputs_file_name
        )

    cwl_file = cwl_loader.load_cwl()
    cwl_file_id = cwl_file.get_workflow_id()

    username = os.getenv("USERNAME")
    api_token = os.getenv("API_TOKEN")

    ades_client = ADESClient(
        workflow_api_url, username, boot_timeout, monitor_timeout, api_token=api_token
    )
    eodhp_client = EODHPClient(resource_catalogue_api_url, username, api_token=api_token)

    try:
        # Check ades is running
        ades_client.check_status()
        # Generate API token
        # api_token = eodhp_client.request_api_token(debug)

        # Set api_token for ADESClient
        # ades_client.set_api_token(api_token)

        # Test API token access
        ades_client.check_api_token()

        # Need to wait after undeployment for a few seconds before workflow is available for deployment
        time.sleep(5)

        # Deploy workflow
        ades_client.deploy_workflow(cwl_file)

        # Check deployment status
        ades_client.check_deployment_status(cwl_file_id)

        # Need to wait after deployment for a few seconds before workflow is available for execution
        time.sleep(5)

        # Execute workflow
        job_id = ades_client.execute_workflow(cwl_file)

        # Monitor workflow execution for success or failure
        results_link = ades_client.monitor_workflow(job_id)

        if debug:
            if os.getenv("AWS_ACCESS_KEY_ID", None) and os.getenv("AWS_SECRET_ACCESS_KEY", None):
                client = boto3.client(
                    "s3",
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                )
            else:
                client = boto3.client("s3")
            eodhp_client.set_client(client)
            # Check in S3 to confirm all outputs are present (debug only)
            eodhp_client.check_outputs_in_s3(results_link)

        # Check token allows outputs to be downloaded
        eodhp_client.check_s3_access_token(cwl_file_id, results_link, debug)
        ## Final result
        logger.info("Test is successful")
    except Exception:
        logger.error("Workflow system test failed")
        raise
    finally:
        # Undeploy test workflow
        ades_client.undeploy_workflow(cwl_file_id)


if __name__ == "__main__":
    cli()
