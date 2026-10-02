# Release the application

## Description

Release a new version. `bump-version.yml` computes the version from Conventional Commits.

## Steps

1. Open a pull request from `dev` to `master`.
2. Merge the pull request.
3. `bump-version.yml` bumps `pyproject.toml`, updates `CHANGELOG.md`, tags `v<version>` and pushes.
4. `bump-version.yml` syncs `uv.lock` and `frontend/package.json`.
5. Merge `master` back into `dev`.
6. If the release ships, build and push images. See [Build and push images](build-push-images.md).

## Rules

* Do not edit the version by hand.
* Do not edit `CHANGELOG.md` by hand.
* Commit types decide the bump. See [Write commits](../git/write-commits.md#version-effect).
