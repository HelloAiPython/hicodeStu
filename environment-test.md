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

- `python3 -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements.txt`
  - Failed with `ProxyError: Tunnel connection failed: 403 Forbidden` when pip accessed `/simple/django/` via configured proxy (`http://proxy:8080`).

- `unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY; . .venv/bin/activate && pip install -r backend/requirements.txt`
  - Failed with `Network is unreachable` when bypassing proxy, indicating direct outbound internet is blocked in this environment.

- `. .venv/bin/activate && pip install Django==5.2.11 -i http://pypi.hub.ace-research.openai.org/simple --trusted-host pypi.hub.ace-research.openai.org`
  - Failed with `No matching distribution found`, and direct `curl` to that mirror URL also returned `403 Forbidden`.

- `curl -I https://pypi.org/simple/django/`
  - Failed with `CONNECT tunnel failed, response 403` from the proxy.

## Conclusion

This container currently cannot install Python packages from PyPI, regardless of using the configured proxy or bypassing it. To run Django tests here, one of the following is needed:

1. A reachable internal PyPI mirror configured via `PIP_INDEX_URL`.
2. Prebuilt wheel files mounted into the workspace for offline installation.
3. Fix access policy for `http://proxy:8080` to allow pip tunneling to PyPI.
