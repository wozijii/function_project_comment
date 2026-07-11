import os
import json
import datetime
import urllib.request
import urllib.error
import urllib.parse

DEFAULT_CALLBACK = os.environ.get('SIM_CALLBACK_URL', 'http://10.100.200.241:18002/api/v1/virtual-simulation/video-path')


def _write_log(entry: dict):
    try:
        base = os.path.dirname(__file__)
        log_path = os.path.normpath(os.path.join(base, '..', 'callback_log.json'))
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def send_video_callback(video_path: str, simulate_id:int, type: int , distance: float, simulate: bool = False, callback_url: str = None, source_name: str = None) -> dict:
    url = callback_url or DEFAULT_CALLBACK
    if source_name is None:
        source_name = os.environ.get('SIM_CALLBACK_SOURCE_NAME')

    if source_name:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}source_name={urllib.parse.quote(source_name)}"

    payload = {"type": type, "simulate_id": simulate_id, "video_path": video_path, "distance": distance, "simulate": simulate}
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_text = resp.read().decode('utf-8')
            result = {"status": "ok", "code": resp.getcode(), "response": resp_text}
            _write_log({
                "timestamp": datetime.datetime.utcnow().isoformat() + 'Z',
                "url": url,
                "payload": payload,
                "result": result
            })
            return result
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode('utf-8')
        except Exception:
            err = str(e)
        result = {"status": "http_error", "code": e.code, "error": err}
        _write_log({
            "timestamp": datetime.datetime.utcnow().isoformat() + 'Z',
            "url": url,
            "payload": payload,
            "result": result
        })
        return result
    except Exception as e:
        result = {"status": "error", "error": str(e)}
        _write_log({
            "timestamp": datetime.datetime.utcnow().isoformat() + 'Z',
            "url": url,
            "payload": payload,
            "result": result
        })
        return result
