# Changelog

## v0.1.1 (2024-09-10)

Add new tests and logging cleanup
- Add test to check availability of workflow logs
- Handle "Too Many Requests" response from workflow runner
- Update test termination step to improve error logging

## v0.1.0 (2024-08-22)

Initial Commit for System Workflow Test
- Added application to test the full system flow for the ADES workflow runner
- Generate token, deploy workflow, execute, monitor, and confirm output availability via HTTPS
