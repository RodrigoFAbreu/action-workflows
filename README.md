# Shared GitHub Actions workflows

Common workflows reused by application repositories for tests, builds,
publication and pull-request validation.

Workflows are in `.github/workflows`. Call them from a CI job using
`RodrigoFAbreu/action-workflows/.github/workflows/<workflow>.yml@main`.
Each workflow declares its supported inputs and secrets.

Calling repositories control triggers, job dependencies and release policy.
