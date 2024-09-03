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

This will create a virtual environment called `venv`, build `requirements.txt` and
`requirements-dev.txt` from `pyproject.toml` if they're out of date, install the Python
and Node dependencies and install `pre-commit`.

It's safe and fast to run `make setup` repeatedly as it will only update these things if
they have changed.

After `make setup` you can run `pre-commit` to run pre-commit checks on staged changes and
`pre-commit run --all-files` to run them on all files. This replicates the linter checks that
run from GitHub actions.

## Building and testing

This component uses `pytest` tests and the `ruff` and `black` linters. `black` will reformat your code in an
opinionated way.

A number of `make` targets are defined:
* `make test`: run tests continuously
* `make testonce`: run tests once
* `make lint`: lint and reformat
* `make dockerbuild`: build a `latest` Docker image (use `make dockerbuild `VERSION=1.2.3` for a release image)
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
python -m system_tests workflow <auth-token-api-url> <ades-api-url> <resource-catalogue-api-url> <path-to-local-workflow-file> <path-to-local-inputs-file>
```
2. Loading workflow files remotely from GitHub
```sh
python -m system_tests workflow <auth-token-api-url> <ades-api-url> <resource-catalogue-api-url> <path-to-remote-workflow-file> <path-to-remote-inputs-file> --github-repo <github-repo-name> --github-branch <github-branch-name>
```

This CLI also supports shorthand arguments for `--github-repo` : `-gr` and `--github-branch` : `-gb`. 

You can also configure the `--debug` flag and two timeouts from the command line, `--boot-timeout` and `--monitor-timeout`, to specify the time to wait for the ADES to become available and for the workflow to finish executing respectively.

You can monitor the test progress via the logging outputs to the command line

## Managing requirements

Requirements are specified in `pyproject.toml`, with development requirements listed separately. Specify version
constraints as necessary but not specific versions. After changing them:

* Run `pip-compile` (or `pip-compile -U` to upgrade requirements within constraints) to regenerate `requirements.txt`
* Run `pip-compile --extra dev -o requirements-dev.txt` (again, add `-U` to upgrade) to regenerate
  `requirements-dev.txt`.
* Run the `pip3 install -r requirements.txt` and `pip3 install -r requirements-dev.txt` commands again and test.
* Commit these files.

If you see the error

```commandline
Backend subprocess exited when trying to invoke get_requires_for_build_wheel
Failed to parse /.../template-python/pyproject.toml
```

then install and run `validate-pyproject pyproject.toml` and/or `pip3 install .` to check its syntax.

To check for vulnerable dependencies, run `pip-audit`.

## Releasing

Ensure that `make lint` and `make test` work correctly and produce no further changes to code formatting before
continuing.

Releases tagged `latest` and targeted at development environments can be created from the `main` branch. Releases for
installation in non-development environments should be created from a Git tag named using semantic versioning. For
example, using

* `git tag 1.2.3`
* `git push --tags`

Normally, Docker images will be built automatically after pushing to the UKEODHP repos. Images can also be created
manually in the following way:

* For versioned images create a git tag.
* Log in to the Docker repository service. For the UKEODHP environment this can be achieved with the following command
  ```AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=... aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 312280911266.dkr.ecr.eu-west-2.amazonaws.com```
  You will need to create an access key for a user with permission to modify ECR first.
* Run `make dockerbuild` (for images tagged `latest`) or `make dockerbuild VERSION=1.2.3` for a release tagged `1.2.3`.
  The image will be available locally within Docker after this step.
* Run `make dockerpush` or `make dockerpush VERSION=1.2.3`. This will send the image to the ECR repository.