# workflow-system-test

This repository provides a full end-to-end systems test of the workflow system included in EODHP. This test is wrapped in a CLI and packaged up into a Docker image that can be deployed to the cluster for triggerable testing.
It runs through the following steps:
1. Request an API token using new auth-agent API
2. Publish a workflow from a git repository
3. Execute the workflow
4. Poll (with reasonable timeout) until final result is available, and check it is successful
5. Check workflow outputs are available in the Resource Catalogue
6. Check expected asset file is available from S3 via HTTPS

# Development of this component

## Getting started

### Install via makefile

```commandline
make setup
```

This will install dependencies using `uv`, generate the lockfile if needed, and install `pre-commit` hooks.

It's safe and fast to run `make setup` repeatedly as it will only update these things if
they have changed.

After `make setup` you can run `make pre-commit` to run pre-commit checks on staged changes and
`make pre-commit-all` to run them on all files. This replicates the linter checks that
run from GitHub actions.

## Building and testing

This component uses `pytest` tests and the `ruff` linter/formatter.

A number of `make` targets are defined:
* `make test`: run tests continuously (watch mode)
* `make testonce`: run tests once
* `make format`: auto-fix lint issues and format code
* `make check`: run all linting, formatting, type checking, and pyproject validation
* `make dockerbuild`: build a `latest` Docker image (use `make dockerbuild VERSION=1.2.3` for a release image)
* `make dockerpush`: push a `latest` Docker image (again, you can add `VERSION=1.2.3`) - normally this should be done
  only via the build system and its GitHub actions.


## Running locally

This repo provides a CLI to allow running of systems-level tests. Currently only a single system test is provided which tests the workflow runner component of the Hub.
To run this code locally you can run the following steps:
* Configure environment variables as found in the `sample-env` file, copy this to a new file named `.env`
* Load the environment variables by running `source .env`
* Run the code from the root of the repository specifying required arguments for the test:
1. Loading workflow files locally
```sh
uv run python -m system_tests workflow <auth-token-api-url> <ades-api-url> <resource-catalogue-api-url> <path-to-local-workflow-file> <path-to-local-inputs-file>
```
2. Loading workflow files remotely from GitHub
```sh
uv run python -m system_tests workflow <auth-token-api-url> <ades-api-url> <resource-catalogue-api-url> <path-to-remote-workflow-file> <path-to-remote-inputs-file> --github-repo <github-repo-name> --github-branch <github-branch-name>
```

This CLI also supports shorthand arguments for `--github-repo` : `-gr` and `--github-branch` : `-gb`.

You can also configure the `--debug` flag and two timeouts from the command line, `--boot-timeout` and `--monitor-timeout`, to specify the time to wait for the ADES to become available and for the workflow to finish executing respectively.

To check that a broken workflow is reported as failed instead of hanging, add `--expect-failure`. The test then passes only if the job fails before the monitor timeout, without a stack trace in its message. `--expect-message <text>` also requires the failure message to contain that text, for example `examples/failing-step-app.cwl examples/failing-step-app-inputs.json --expect-failure --expect-message fail_on_purpose`.

You can monitor the test progress via the logging outputs to the command line

## Managing requirements

Dependencies are specified in `pyproject.toml`. After changing them:

* Run `uv sync` to update the lockfile and install the new dependencies.
* Run `make check` to verify everything is correct.
* Commit the updated `pyproject.toml` and `uv.lock` files.

## Releasing

Ensure that `make check` and `make testonce` work correctly and produce no errors before
continuing.

Releases tagged `latest` and targeted at development environments can be created from the `main` branch. Releases for
installation in non-development environments should be created from a Git tag named using semantic versioning. For
example, using

* `git tag v1.2.3`
* `git push --tags`

Docker images will be built automatically by GitHub Actions after pushing to the EO-DataHub repos.
