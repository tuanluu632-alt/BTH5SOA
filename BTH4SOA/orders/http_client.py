import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

def request_json(url, method="GET", headers=None, timeout=4):
    request = Request(url, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            payload = {}
        return exc.code, payload
    except (URLError, TimeoutError, OSError) as exc:
        raise ConnectionError(str(exc)) from exc
