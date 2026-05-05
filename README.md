# cronwrap

Lightweight wrapper for cron jobs that adds logging, alerting, and retry logic.

---

## Installation

```bash
pip install cronwrap
```

---

## Usage

Wrap any command in your crontab to get automatic logging, failure alerts, and retries:

```bash
# Basic usage
cronwrap run "python /path/to/script.py"

# With options
cronwrap run "python /path/to/script.py" \
  --retries 3 \
  --alert-email ops@example.com \
  --log-file /var/log/myjob.log
```

You can also use it programmatically:

```python
from cronwrap import JobRunner

runner = JobRunner(
    command="python /path/to/script.py",
    retries=3,
    alert_email="ops@example.com",
    log_file="/var/log/myjob.log"
)

runner.run()
```

**Example crontab entry:**

```
0 2 * * * cronwrap run "python /opt/jobs/nightly_sync.py" --retries 2 --alert-email ops@example.com
```

---

## Features

- 📋 Structured logging for every job run
- 🔁 Configurable retry logic on failure
- 📧 Email or webhook alerts on job failure
- ⏱️ Execution time tracking
- 🪶 Zero heavy dependencies

---

## License

MIT © cronwrap contributors