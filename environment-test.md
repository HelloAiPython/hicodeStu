# Environment installation attempts

## Commands and results

- `python3 --version`
  - Output: `Python 3.10.19`

- `apt-get update`
  - Failed with `403 Forbidden` errors when accessing Ubuntu repositories via proxy.

- `python3 -m venv /tmp/django-test-venv`
  - Succeeded.

- `/tmp/django-test-venv/bin/pip install Django==5.2.11`
  - Failed with `403 Forbidden` proxy errors reaching PyPI.
