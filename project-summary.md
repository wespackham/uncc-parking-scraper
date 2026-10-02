# UNCC Parking Scraper — Project Summary

## What This Project Is

A Python application that automatically tracks real-time parking availability across all parking decks at UNC Charlotte. Every 5 minutes, it hits the university's live parking feed, captures a snapshot of how full each lot is, and stores that data in a cloud database (Supabase/PostgreSQL). The goal is to build a historical dataset that can power a parking trends dashboard.

---

## What Was Built

### 1. Automated Scheduling with systemd

The scraper doesn't run manually — it runs itself. Using **systemd timers** (Linux's built-in job scheduler), the scraper fires automatically every 5 minutes. This is the same system that powers background services on production Linux servers. The app runs as a one-shot background service — it wakes up, does its job, and exits cleanly.

A second timer was added to send a daily health report every night at 10 PM.

**Why this matters:** This is how real production systems handle scheduled work. No cron hacks, no always-running process burning resources — just an event-driven service that only runs when needed.

### 2. Automated Deployment via GitHub Actions (CI/CD)

Pushing code to the `main` branch on GitHub automatically deploys it to a live AWS EC2 server — no manual SSH, no FTP, no copy-paste. The GitHub Actions workflow:

1. Detects a push to `main` that touches relevant files (`src/`, `requirements.txt`, service files)
2. SSHes into the EC2 instance using a stored secret key
3. Pulls the latest code
4. Installs any new dependencies
5. Copies the systemd service files into place
6. Reloads systemd and restarts both timers

This means: write code locally → commit → push → it's live on the server. No manual steps.

**Why this matters:** This is standard DevOps practice for any production web service or data pipeline. It eliminates human error from deployments and makes the project maintainable by anyone with repo access.

### 3. Discord Webhook Notifications (Alerting)

If anything goes wrong — the university's parking feed is down, the JSON comes back malformed, or there's an unexpected server error — the scraper now **sends an alert to a Discord channel in real time**. This was built as a lightweight notifier module (`src/notifier.py`) that any part of the app can call.

Errors are caught at three levels:
- Network failures (server unreachable, timeout)
- Data format failures (response isn't valid JSON)
- Unexpected exceptions (anything else)

Each case sends a descriptive Discord message so the issue can be diagnosed without ever SSH-ing into the server.

**Why this matters:** Observability is what separates a toy project from a real system. Without alerting, a broken scraper could silently miss days of data with no indication anything went wrong.

### 4. Daily Health Report

Every night at 10 PM, an automated report is sent to Discord summarizing the past 24 hours of data collection. The scraper is expected to collect **288 snapshots per day** (one every 5 minutes × 24 hours). The report compares actual vs. expected:

- ✅ **288/288** — everything is healthy
- ⚠️ **Partial count** — some snapshots were missed, degraded performance
- 🚨 **0/288** — scraper is likely down, immediate attention needed

**Why this matters:** Rather than checking manually or waiting for a user to notice gaps in the data, the system proactively reports its own health every day.

### 5. Automated Test Suite

A full unit test suite was written covering all the critical logic paths:

**Scraper tests (`test_scraper.py`):**
- Correctly parses and inserts a valid parking snapshot
- Skips blank lines and non-data lines in the stream response
- Gracefully handles parking lots with missing fields
- Does not insert anything when the snapshot is empty
- Handles network errors without crashing
- Handles malformed JSON without crashing
- Only processes the first data event per run (as designed)

**Notifier tests (`test_notifier.py`):**
- Correctly sends the message payload to the Discord webhook URL
- Silently swallows exceptions so a notification failure never crashes the scraper

**Daily report tests (`test_daily_report.py`):**
- Sends a success message when all 288 snapshots are present
- Sends a warning when the count is partial
- Sends a critical alert when the count is zero

All tests use mocks so they run entirely offline — no real database or network calls needed during testing.

**Why this matters:** Tests prove the logic is correct and make it safe to change the code later without accidentally breaking something. The mock-based approach means tests run fast and reliably in CI.

### 6. Local JSONL Buffering And Ordered Retry

The scraper now buffers every successful live snapshot to disk before it tries to write anything to Supabase. Buffered rows are stored in `logs/pending_snapshots.jsonl` as newline-delimited JSON records containing:

- `created_at`
- `data`

On each run, the scraper:

1. Fetches the live parking snapshot
2. Appends it to the local JSONL buffer
3. Replays buffered rows to Supabase in order
4. Stops on the first failed insert and leaves the remaining rows on disk

A manual replay mode was also added:

```bash
python main.py --flush-only
```

This lets the server recover automatically from temporary Supabase failures, expired keys, or short network outages without silently losing parking history.

**Why this matters:** The original scraper could miss data permanently if Supabase was unavailable at write time. Local-first buffering turns that failure mode into a temporary backlog instead of permanent data loss.

---

## Technology Stack

| Layer | Tool |
|---|---|
| Language | Python |
| HTTP / Streaming | `requests` |
| Database | Supabase (PostgreSQL) |
| Scheduling | systemd timers |
| Alerting | Discord webhooks |
| Deployment | GitHub Actions → AWS EC2 |
| Testing | pytest, unittest.mock |
| Config / Secrets | `.env` / GitHub Secrets |
| Local durability | JSONL buffer in `logs/pending_snapshots.jsonl` |

---

## Skills Demonstrated

- **Cloud infrastructure:** Deployed and maintained a Python application on AWS EC2
- **CI/CD pipelines:** Built a GitHub Actions workflow that auto-deploys on push
- **Linux systems:** Configured systemd services and timers for scheduled execution
- **Data engineering:** Designed a repeatable data collection pipeline storing time-series parking snapshots
- **Observability:** Built real-time alerting and daily health reporting
- **Reliability engineering:** Added local-first buffering and ordered retry for transient database failures
- **Software testing:** Wrote a unit test suite with full mock isolation
- **API integration:** Consumed a live server-sent events (SSE) stream and a Discord webhook API
