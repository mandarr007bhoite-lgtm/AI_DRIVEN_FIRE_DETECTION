import os
import csv
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

try:
    from twilio.rest import Client  # type: ignore
except Exception:  # Twilio may not be installed in all environments
    Client = None  # type: ignore


def _get_twilio_client() -> Optional["Client"]:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token or Client is None:
        print("[SMS] Twilio client not configured or library missing.")
        return None
    return Client(account_sid, auth_token)


def send_fire_alert_sms(to_number: str, message: str) -> bool:
    """Send an SMS using Twilio. Returns True on success, False otherwise."""
    result = send_sms(to_number, message)
    return bool(result.get("success"))


def send_fire_alert_voice(to_number: str, tts_message: str) -> bool:
    """Place a voice call with configurable alarm loops/audio if ENABLE_TWILIO_VOICE=true.

    Env options:
    - ENABLE_TWILIO_VOICE=true
    - ALARM_VOICE_LOOPS (default 3)
    - ALARM_VOICE_MESSAGE (override message)
    - ALARM_VOICE_AUDIO_URL (if set, plays this audio instead of TTS)
    """
    if os.getenv("ENABLE_TWILIO_VOICE", "false").lower() != "true":
        return False
    client = _get_twilio_client()
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    if client is None or not from_number:
        return False

    try:
        try:
            loops = int(os.getenv("ALARM_VOICE_LOOPS", "3"))
        except ValueError:
            loops = 3
        say_text = os.getenv("ALARM_VOICE_MESSAGE", tts_message)
        audio_url = os.getenv("ALARM_VOICE_AUDIO_URL")

        if audio_url:
            twiml = f"<Response><Play loop=\"{loops}\">{audio_url}</Play></Response>"
        else:
            twiml = f"<Response><Say voice=\"alice\" loop=\"{loops}\">{say_text}</Say></Response>"

        client.calls.create(
            to=to_number,
            from_=from_number,
            twiml=twiml,
        )
        return True
    except Exception:
        return False


_last_sms_at: Dict[str, datetime] = {}


def _now_ist() -> datetime:
    # Compute IST as UTC+05:30 independent of system timezone
    return datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(hours=5, minutes=30)


def _now_ist_str() -> str:
    return _now_ist().strftime("%Y-%m-%d %H:%M:%S")


def _log_csv(event_type: str, payload: Dict[str, Any]) -> None:
    csv_path = os.path.join(os.getcwd(), "fire_log.csv")
    is_new = not os.path.exists(csv_path)
    try:
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp_ist",
                    "event_type",
                    "to",
                    "status",
                    "sid",
                    "message",
                    "intensity",
                ],
            )
            if is_new:
                writer.writeheader()
            row = {
                "timestamp_ist": _now_ist_str(),
                "event_type": event_type,
                "to": payload.get("to"),
                "status": payload.get("status"),
                "sid": payload.get("sid"),
                "message": payload.get("message"),
                "intensity": payload.get("intensity"),
            }
            writer.writerow(row)
    except Exception:
        # Swallow logging errors; do not break detection/alerts
        pass


def send_sms(to_number: str, message: str, cooldown_seconds: Optional[int] = None, intensity: Optional[str] = None) -> Dict[str, Any]:
    """Send SMS with cooldown and CSV logging. Returns details including success, status, sid.

    Cooldown is tracked per-recipient. If within cooldown, skips sending and returns success=False, status="cooldown".
    Uses TWILIO_MESSAGING_SERVICE_SID if set; otherwise TWILIO_FROM_NUMBER.
    """
    if cooldown_seconds is None:
        try:
            cooldown_seconds = int(os.getenv("SMS_COOLDOWN_SECONDS", "60"))
        except ValueError:
            cooldown_seconds = 60

    now = _now_ist()
    last_sent = _last_sms_at.get(to_number)
    if last_sent is not None and (now - last_sent).total_seconds() < cooldown_seconds:
        result = {"success": False, "status": "cooldown", "sid": None, "to": to_number}
        _log_csv("sms", {"to": to_number, "status": "cooldown", "sid": None, "message": message, "intensity": intensity})
        return result

    client = _get_twilio_client()
    messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    if client is None or (not messaging_service_sid and not from_number):
        result = {"success": False, "status": "not_configured", "sid": None, "to": to_number}
        print(f"[SMS] Not configured. messaging_service_sid={bool(messaging_service_sid)} from_number={bool(from_number)}")
        _log_csv("sms", {"to": to_number, "status": "not_configured", "sid": None, "message": message, "intensity": intensity})
        return result

    try:
        if messaging_service_sid:
            msg = client.messages.create(
                to=to_number,
                messaging_service_sid=messaging_service_sid,
                body=message,
            )
        else:
            msg = client.messages.create(
                to=to_number,
                from_=from_number,
                body=message,
            )
        _last_sms_at[to_number] = now
        result = {"success": True, "status": getattr(msg, "status", None), "sid": getattr(msg, "sid", None), "to": to_number}
        print(f"[SMS] Sent to {to_number}. status={result['status']} sid={result['sid']}")
        _log_csv("sms", {"to": to_number, "status": result["status"], "sid": result["sid"], "message": message, "intensity": intensity})
        return result
    except Exception as exc:
        result = {"success": False, "status": "error", "sid": None, "to": to_number, "error": str(exc)}
        print(f"[SMS] Error sending to {to_number}: {exc}")
        _log_csv("sms", {"to": to_number, "status": "error", "sid": None, "message": message, "intensity": intensity})
        return result


def log_detection(intensity: str) -> None:
    """Log a detection event to CSV with IST timestamp."""
    _log_csv("detection", {"to": None, "status": "detected", "sid": None, "message": "Fire detected", "intensity": intensity})


