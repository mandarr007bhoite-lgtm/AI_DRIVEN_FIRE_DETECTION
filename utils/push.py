import os
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

try:
    from pywebpush import webpush, WebPushException  # type: ignore
except Exception:
    webpush = None  # type: ignore
    WebPushException = Exception  # type: ignore


def _now_ist_str() -> str:
    return (datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")


def send_web_push_to_all(subscriptions: List[Dict[str, Any]], title: str, body: str) -> List[Dict[str, Any]]:
    """Send a web push notification to all given subscriptions. Returns result list."""
    vapid_private = os.getenv("VAPID_PRIVATE_KEY")
    vapid_email = os.getenv("VAPID_EMAIL", "admin@example.com")
    if webpush is None or not vapid_private:
        return [{"success": False, "error": "not_configured"}]

    vapid_claims = {
        "sub": f"mailto:{vapid_email}"
    }

    results: List[Dict[str, Any]] = []
    payload = json.dumps({"title": title, "body": body, "timestamp": _now_ist_str()})
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                },
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims=vapid_claims,
                ttl=60,
            )
            results.append({"success": True})
        except WebPushException as exc:  # type: ignore
            results.append({"success": False, "error": str(exc)})
        except Exception as exc:
            results.append({"success": False, "error": str(exc)})

    return results



