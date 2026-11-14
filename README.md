# Shared GitHub Actions workflows

Reusable workflows for application repositories. Callers own their release
version calculation, repository-specific validation and release completion gates.

| Workflow | Contract |
| --- | --- |
| `pr-title.yml` | Validates the shared Conventional Commit grammar |
| `promote-image.yml` | Copies an already released GHCR manifest to latest, preserving its format and architectures |
| `npm-build-publish.yml` | Installs locked dependencies, runs selected scripts and optionally publishes an npm package |
| `java-build-publish.yml` | Runs Maven Wrapper verify and optionally deploys Maven artifacts |

The language workflows publish package artifacts. Container image build and
multi-platform assembly remain with the application release pipeline until their
build contracts can be shared without losing project checks. SignalHub's backend
and app releases retain their own runtime and signing validations.

## Calling the workflows

Use a reviewed release tag such as `v1.0.0`, or the compatible `v1` series tag.
Before the first reviewed release, the workflow files are available on their
review branch for validation. First merge and validate the shared workflow
repository, then publish its release tags, then adopt the tagged calls.

```yaml
jobs:
  title:
    uses: RodrigoFAbreu/action-workflows/.github/workflows/pr-title.yml@v1
  latest:
    needs: [version, image, release]
    if: needs.version.outputs.next != ''
    permissions:
      contents: read
      packages: write
    uses: RodrigoFAbreu/action-workflows/.github/workflows/promote-image.yml@v1
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

This repository contains generic CI code. Its public visibility is required for
public caller repositories. Publication awaits Rodrigo's explicit visibility
approval. Credentials and personal infrastructure configuration stay outside it.
