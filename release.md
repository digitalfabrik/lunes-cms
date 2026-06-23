# Release

## Staging Release

A staging release is automatically created on every merge to the `develop` branch.

The CI pipeline runs the following steps:

1. **Bump dev version** — increments the alpha version based on the latest version on TestPyPI
2. **Build package** — builds the Python package (requires a passing e2e test suite)
3. **Publish package** — uploads the package to [TestPyPI](https://test.pypi.org/project/lunes-cms/)

The staging release is installed nightly at **03:30** on the test server.

## Production Release

A production release is triggered automatically when a version tag is pushed to `main`.

The tag is created by the CI pipeline on every merge to `main`:

1. **Bump version** — increments the version and creates an annotated Git tag
2. **Tag push** — triggers the deploy pipeline
3. **Build & publish** — builds the package and publishes it to [PyPI](https://pypi.org/project/lunes-cms/)
4. **Create release** — creates a GitHub release with changelog
5. **Notify** — sends a Mattermost notification

The production release will be installed on Fridays during the maintenance window.
