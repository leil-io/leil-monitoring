# Contributing to Leil Monitoring

Thanks for taking the time to contribute.

This project contains the Leil Monitoring UI, API, client code, Docker setup,
tests, and package build configuration.

## Questions and Issues

Before opening an issue, please check the [README](README.md) and search
existing issues.

When reporting a bug, include:

- What you expected to happen.
- What actually happened.
- Steps to reproduce the problem.
- Your Python version, OS, and whether you used Docker or a local environment.
- Relevant `SAUNAFS_*` environment variables.
- Logs, tracebacks, screenshots, or API responses when useful.

For feature requests, describe the current behavior, the desired behavior, and
why the change would help users monitoring LeilFS deployments.

## Development Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e ".[dev,test]"
```

Run the monitoring UI:

```bash
uvicorn --host 0.0.0.0 --reload --app-dir src leil_monitoring.main:app
```

Run the API:

```bash
uvicorn --host 0.0.0.0 --port 8001 --reload --app-dir src leil_api.main:app
```

The monitoring UI is available at `http://127.0.0.1:8000`.
The API docs are available at `http://127.0.0.1:8001/docs`.

## Docker Development

Copy the example environment file and start the development compose stack:

```bash
cp .env.example .env
docker compose -f compose-dev.yaml build
docker compose -f compose-dev.yaml up
docker compose -f compose-dev.yaml down
```

You can also use:

```bash
./run-dev.sh
```

Edit `.env` if you need to change the master host, master port, application
host, or application ports.

## Tests

Run non-integration tests:

```bash
pytest tests -m "not integration"
```

Integration tests require a reachable LeilFS master:

```bash
SAUNAFS_MASTER_HOST=127.0.0.1 SAUNAFS_MASTER_PORT=9421 pytest tests -m integration
```

The CI compose setup for integration tests is in
[docker-compose.ci.yaml](docker-compose.ci.yaml).

When changing imports in UI or API modules, make sure non-integration test
collection does not require a live master connection.

## Style

For Python changes, use:

```bash
black src tests
flake8 src tests
mypy src
pytest tests -m "not integration"
```

The repository ignores `E501` through [pycodestyle.cfg](pycodestyle.cfg).

Use focused changes. Avoid mixing unrelated formatting, documentation, and
behavior changes in one pull request.

## Commits

Use Conventional Commits:

```text
fix(api): handle missing disk stats
feat(ui): add chunkserver filter
docs: update Docker setup
test(client): cover malformed response
```

Common scopes include `api`, `monitoring`, `client`, `ui`, `templates`, `tests`,
`docker`, `packaging`, and `ci`.

Sign off commits (required):

```bash
git commit -s
```

By submitting a contribution, you agree to the Developer Certificate of Origin
(**DCO**): <https://developercertificate.org/>.

## Building Packages

Build package artifacts through [Dockerfile.build](Dockerfile.build):

```bash
docker build \
    --tag leil-monitoring:packages \
    --target packages \
    --output ./dist \
    --file Dockerfile.build \
    .
```

The build outputs are written to `dist` and may include Debian packages and
Python wheels.

## Before Opening a Pull Request

Make sure:

- The change has appropriate tests.
- Non-integration tests pass.
- Integration behavior is tested when the change depends on a live LeilFS
  master.
- Documentation is updated when behavior, commands, configuration, or packaging
  changes.
- The pull request explains what changed and how it was tested.
