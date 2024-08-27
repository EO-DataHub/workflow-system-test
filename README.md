# workflow-system-test

This repository provides a full end-to-end systems test of the workflow system included in EODHP. This test will be packaged up into a Docker image that can be deployed to the cluster for triggerable testing.
It runs through the following steps:
1. Request an API token using new auth-agent API
2. Publish a workflow from a git repository
3. Execute the workflow
4. Poll (with reasonable timeout) until final result is available, and check it is successful
5. Check expected file is available from S3 via HTTPS