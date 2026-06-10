# long-batch

Python batch jobs for synchronizing legislation from the 国家法律法规数据库
(National Database of Laws and Regulations of the People's Republic of China)
into a local text corpus for search/chat systems.

## Layout

- `shell/`: cron-facing shell entrypoints.
- `domain/`: Python job implementation and source clients.
- `/app/legislation/laws/<law title>/law.txt`: extracted law text in Docker.
- `/app/legislation/laws/<law title>/metadata.json`: generated local metadata.
- `/app/legislation/state/law_index.json`: sync index used to detect new and updated laws.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Configure one or more official listing/search URLs before running:

```bash
export NATIONAL_LAW_DB_INDEX_URLS="https://example.official-listing-url"
```

Optional settings:

```bash
export LAW_DATA_DIR="data"
export LAW_SYNC_REQUEST_DELAY_SECONDS="0.5"
export LAW_SYNC_REQUEST_TIMEOUT_SECONDS="30"
```

`LAW_DATA_DIR` defaults to `/app/legislation` because production runs inside a
Docker container. Set it to `data` for local development.

## Run

```bash
./shell/check_national_law_db.sh --limit 10
./shell/update_national_law_db.sh
./shell/sync_due_national_law_db.sh
```

The check script compares remote metadata with the local index and writes
nothing. It exits `0` when nothing changed, `2` when new or updated laws are
available, and `1` on failures.

The update script performs the same comparison, then writes only new or changed
laws. Both scripts are safe to invoke from cron and append logs under
`${LOG_DIR:-logs}`.

The due-sync script is intended for cron. It can run every day, but it only
calls the update job when at least 15 days have elapsed since the last
successful sync. Override the interval with `SYNC_INTERVAL_DAYS`.

## Docker

Build locally:

```bash
docker build -t long-batch .
```

Run as a long-lived container and execute jobs with `docker exec` or host cron:

```bash
docker run -d \
  --name long-batch \
  --restart always \
  -e LAW_DATA_DIR=/app/legislation \
  -e LOG_DIR=/app/log/long-batch \
  -e NATIONAL_LAW_DB_INDEX_URLS="https://example.official-listing-url" \
  -v /app/legislation:/app/legislation \
  -v /app/log/long-batch:/app/log/long-batch \
  long-batch

docker exec long-batch /app/shell/check_national_law_db.sh --limit 10
docker exec long-batch /app/shell/update_national_law_db.sh
docker exec long-batch /app/shell/sync_due_national_law_db.sh
```

The `/app/legislation` volume is the persistence bridge. Scraped laws survive
container replacement because `laws/`, `state/`, and `tmp/` live under that
mounted directory.

## Cron

Use host cron to execute jobs inside the long-running container:

```cron
10 3 * * * docker exec long-batch /app/shell/sync_due_national_law_db.sh >> /app/log/long-batch/cron.log 2>&1
```

This runs daily at 03:10, while `sync_due_national_law_db.sh` enforces the
15-day interval using `/app/legislation/state/last_sync_epoch`. This is more
accurate than cron day-of-month syntax like `*/15`, which runs on fixed calendar
days instead of every 15 elapsed days.

See `ops/crontab.example` for a complete host crontab example.

## CI/CD

GitHub Actions workflow:

- `.github/workflows/docker-cicd.yml`
- builds Docker images for pull requests
- pushes GHCR images for pushes to `main`
- deploys the `latest` image over SSH on `main`
- mounts `/app/legislation` and `/app/log/long-batch` from the host into the
  container

Required secrets are the same as your MCP deployment:

- `HOST`
- `USERNAME`
- `SSH_KEY`

Optional deployment secret:

- `NATIONAL_LAW_DB_INDEX_URLS`: comma-separated official listing/search URLs
  passed into the deployed container.

## Current Sync Behavior

The update job discovers remote legislation metadata, compares it with
`/app/legislation/state/law_index.json`, and writes new or changed laws locally.
For PDF sources, it downloads the PDF to `/app/legislation/tmp`, extracts text
into `law.txt`, and then removes the temporary PDF.

The source client is intentionally isolated in
`domain/clients/national_law_db.py` so the site's concrete search/list API can
be upgraded without changing storage, extraction, or cron entrypoints.
