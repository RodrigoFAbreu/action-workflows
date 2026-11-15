# Shared GitHub Actions workflows

Reusable workflows for application repositories. Callers own their release
version calculation, repository-specific validation and release completion gates.

| Workflow | Contract |
| --- | --- |
| `python-tests.yml` | Sets up Python, installs optional requirements and runs repository tests and associated validation |
| `java-tests.yml` | Runs Maven verify, including unit/integration tests and verification plugins |
| `npm-tests.yml` | Runs JavaScript/TypeScript package tests and an optional build |
| `pr-title.yml` | Validates the shared Conventional Commit grammar |
| `promote-image.yml` | Copies an already released GHCR manifest to latest, preserving its format and architectures |
| `npm-build-publish.yml` | Installs locked dependencies, runs selected scripts and optionally publishes an npm package |
| `java-build-publish.yml` | Runs Maven Wrapper verify and optionally deploys Maven artifacts |
| `gitops-validate.yml` | Installs Helm/schema validators and runs the caller repository's tests and GitOps validation script |

The language workflows publish package artifacts. Container image build and
multi-platform assembly remain with the application release pipeline until their
build contracts can be shared without losing project checks. SignalHub's backend
and app releases retain their own runtime and signing validations.

## Calling the workflows

Call reusable workflows through `@main`. Reviewed merges to this protected
branch become available to callers on their next workflow run. Workflow changes
use PRs and pass Workflow checks. Consumers follow the branch directly.

```yaml
jobs:
  title:
    uses: RodrigoFAbreu/action-workflows/.github/workflows/pr-title.yml@main
  latest:
    needs: [version, image, release]
    if: needs.version.outputs.next != ''
    permissions:
      contents: read
      packages: write
    uses: RodrigoFAbreu/action-workflows/.github/workflows/promote-image.yml@main
    with:
      image: ghcr.io/example/application
      source: ghcr.io/example/application@${{ needs.image.outputs.digest }}
```

Keep an existing required-check name through a caller-owned final gate when
moving its implementation into a reusable job. The gate must fail when its
required reusable jobs fail or are cancelled.

The promotion caller must depend on complete release success. Supply a digest
from that release and the same repository. Caller GITHUB_TOKEN permissions apply
to its own packages. No cluster credentials are needed.

For package publishing, pass the optional token explicitly from a repository
Secret and enable `publish` only in the intended release job. Pull-request
publishing fails. npm uses package.json and registry settings, while Maven uses
the project's distributionManagement and selected server ID. Empty test or build
script names explicitly omit those npm stages. Toolchain versions are selected
by the caller.

This public repository contains generic CI code for public and private callers.
Credentials and personal infrastructure configuration stay outside it.

## Orchestration and manual execution

Caller entry points select events and sequence reusable jobs. A CI or Main
workflow runs checks for pull requests and pushes, then calls the application's
release workflow for a validated main commit. Reusable application workflows
use workflow_call, with workflow_dispatch for meaningful isolated runs.

The shared title workflow accepts a manual title check. The shared npm and Maven
workflows can be dispatched against a public source repository with explicit
toolchain settings. Publication is off by default and requires the corresponding
repository Secret. Normal reusable calls check out the caller repository.

Image promotion is call-only because it belongs after the caller's completed
release gate. Retry its job from that release run. GitOps can keep its existing
single validation workflow directly when shared orchestration adds no value.

## Shared language tests

Application CI runs its test jobs for pull requests and pushes to main. A release
job depends on successful validation and runs for a main push. The release
workflow is callable by that CI entry point.

- Python callers use python-tests.yml with their supported versions, optional
  requirements file and repository test command. An optional additional command
  retains workflow linting after a failed primary check.
- JavaScript and TypeScript callers use npm-tests.yml.
  npm ci, the selected test script and build script run in the caller directory.
- Java callers use java-tests.yml. Maven verify runs
  the project's tests, build and verification plugins. An optional prerequisite
  command checks project-specific contracts before Maven starts.

Commands are reviewed repository code supplied by the caller. Shared workflows
handle toolchains and execution, and application scripts select their assertions.
Python, npm and Java test workflows all have manual dispatch entry points.
The Java and npm test workflows reuse the package workflow implementations with
publication disabled. Package publication remains available through the existing
build-publish workflows.
