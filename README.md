# Shared GitHub Actions workflows

Reusable workflows for application repositories. Callers own their release
version calculation, repository-specific validation and release completion gates.

| Workflow | Contract |
| --- | --- |
| `python-tests.yml` | Sets up Python, installs optional requirements and discovers unittest suites from configured directories |
| `java-tests.yml` | Runs Maven verify, including unit/integration tests and verification plugins |
| `npm-tests.yml` | Runs npm test in the caller package |
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

The shared title workflow accepts a manual title check. Language test workflows
are called from the consumer CI or its manually dispatched component workflow.
Checkout uses the calling repository and triggering revision. The test workflows
have no repository override input.

Image promotion is call-only because it belongs after the caller's completed
release gate. Retry its job from that release run. GitOps can keep its existing
single validation workflow directly when shared orchestration adds no value.

## Shared language tests

Application CI runs its test jobs for pull requests and pushes to main. A release
job depends on successful validation and runs for a main push. The release
workflow is callable by that CI entry point.

- Python callers use python-tests.yml. It runs python -m unittest discover with
  test-directory defaulting to tests and test-pattern defaulting to test*.py.
  Optional working-directory, top-level-directory, requirements-file and
  package-directory inputs configure imports and dependencies. Paths are
  relative to the working directory. cache-dependency-path is repository-relative.
- Java callers use java-tests.yml with the Java version and project directory.
  Maven verify runs the project's tests and verification plugins.
- JavaScript and TypeScript callers use npm-tests.yml with the Node.js version
  and package directory. npm ci installs locked dependencies, then npm test runs
  the package's test script.

Custom lint, build checks and project assertions belong in caller-owned jobs.
The shared language workflows own the test commands. The Java and npm test
workflows reuse the package implementations with publication disabled.

Example Python caller configuration:

```yaml
jobs:
  tests:
    uses: RodrigoFAbreu/action-workflows/.github/workflows/python-tests.yml@main
    with:
      python-version: '3.12'
      test-directory: scripts/release
```

## Main-branch interface migration

The Python test-command and after-test-command inputs are temporarily accepted
for existing main-branch callers. Existing docs main still supplies test-command.
New calls use the structured test-directory interface. Merge this shared change,
validate and merge the consumer PRs, then remove the two deprecated inputs and
their legacy steps after confirming no reviewed caller still uses them.
This ordering preserves existing CI while all consumers follow main.
