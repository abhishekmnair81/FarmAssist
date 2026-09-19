import httpx
import base64
import os
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from app.config import settings

def get_headers():
    return {
        "X-API-Key": settings.OPENWA_API_KEY,
        "Authorization": f"Bearer {settings.OPENWA_API_KEY}",
        "Content-Type": "application/json"
    }

def print_banner():
    print("=" * 60, flush=True)
    print("🌾 FarmAssist - Connect to WhatsApp (OpenWA Gateway) 🌾", flush=True)
    print("=" * 60, flush=True)
    print(f"Gateway URL:   {settings.OPENWA_API_URL}", flush=True)
    print(f"Session ID:    {settings.OPENWA_SESSION_ID}", flush=True)
    print("=" * 60 + "\n", flush=True)

def get_session_info():
    url = f"http://127.0.0.1:2785/api/sessions/{settings.OPENWA_SESSION_ID}"
    try:
        r = httpx.get(url, headers=get_headers(), timeout=5.0)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[Error querying session]: {e}")
    return None

def ensure_session():
    info = get_session_info()
    if not info:
        print(f"Session '{settings.OPENWA_SESSION_ID}' not found. Creating session...")
        create_url = "http://127.0.0.1:2785/api/sessions"
        r = httpx.post(create_url, headers=get_headers(), json={"name": "default"}, timeout=10.0)
        if r.status_code in [200, 201]:
            created = r.json()
            settings.OPENWA_SESSION_ID = created.get("id")
            print(f"Created session with ID: {settings.OPENWA_SESSION_ID}")
            return created
        else:
            print(f"Failed to create session: {r.status_code} - {r.text}")
            return None
    return info

def start_session():
    url = f"http://127.0.0.1:2785/api/sessions/{settings.OPENWA_SESSION_ID}/start"
    try:
        httpx.post(url, headers=get_headers(), timeout=5.0)
    except Exception:
        # Launching Chromium may exceed standard timeout; it continues in background
        pass

def register_webhook():
    url = f"http://127.0.0.1:2785/api/sessions/{settings.OPENWA_SESSION_ID}/webhooks"
    payload = {
        "url": "http://fastapi-bot:8000/webhook",
        "events": ["message.received", "session.status"]
    }
    try:
        r = httpx.post(url, headers=get_headers(), json=payload, timeout=5.0)
        if r.status_code in [200, 201]:
            print("Webhook registered successfully (http://fastapi-bot:8000/webhook)")
    except Exception as e:
        print(f"[Notice]: Webhook registration: {e}")

def fetch_and_save_qr():
    url = f"http://127.0.0.1:2785/api/sessions/{settings.OPENWA_SESSION_ID}/qr"
    try:
        r = httpx.get(url, headers=get_headers(), timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            b64 = data.get("qrCode", "")
            if b64.startswith("data:image/png;base64,"):
                b64 = b64.split(",", 1)[1]
            if b64:
                img_data = base64.b64decode(b64)
                qr_path = os.path.join(BASE_DIR, "whatsapp_qr.png")
                with open(qr_path, "wb") as f:
                    f.write(img_data)
                return qr_path
    except Exception:
        pass
    return None

def request_pairing_code(phone: str):
    url = f"http://127.0.0.1:2785/api/sessions/{settings.OPENWA_SESSION_ID}/pairing-code"
    digits = "".join(ch for ch in phone if ch.isdigit())
    payload = {"phoneNumber": digits}
    try:
        r = httpx.post(url, headers=get_headers(), json=payload, timeout=15.0)
        if r.status_code in [200, 201]:
            code = r.json().get("code") or r.json().get("pairingCode")
            return code
        else:
            print(f"Error requesting pairing code ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"Exception requesting pairing code: {e}")
    return None

def main():
    print_banner()
    session = ensure_session()
    if not session:
        print("Could not initialize session with OpenWA. Ensure docker-compose is running.", flush=True)
        return

    register_webhook()
    start_session()
    
    status = session.get("status")
    print(f"Current session status: {status}", flush=True)
    if status in ["WORKING", "authenticated", "ready"]:
        print("\n✅ WhatsApp is ALREADY CONNECTED!", flush=True)
        print(f"Connected as: {session.get('pushName', 'Unknown')} ({session.get('phone', 'N/A')})\n", flush=True)
        return

    print("\nFetching latest WhatsApp QR code...", flush=True)
    qr_path = None
    for _ in range(10):
        qr_path = fetch_and_save_qr()
        if qr_path:
            break
        time.sleep(1.0)

    if qr_path:
        print("\n" + "=" * 60, flush=True)
        print("📲 HOW TO CONNECT YOUR WHATSAPP:", flush=True)
        print("=" * 60, flush=True)
        print(f"1. Open WhatsApp on your phone", flush=True)
        print(f"2. Tap Settings (or 3 dots) -> Linked Devices -> Link a Device", flush=True)
        print(f"3. Scan the QR code saved at:", flush=True)
        print(f"   file:///{qr_path.replace(chr(92), '/')}", flush=True)
        print(f"   (You can also view it in your browser at: http://localhost:2785)", flush=True)
        print("=" * 60 + "\n", flush=True)
        
        # Try to open the QR image automatically in Windows default photo viewer
        try:
            os.startfile(qr_path)
            print("Opened QR code image in your image viewer!", flush=True)
        except Exception:
            pass
    else:
        print("QR code is generating. You can view the live QR in your browser at: http://localhost:2785", flush=True)

    print("\nWaiting for WhatsApp link (polling every 3 seconds)...", flush=True)
    print("Press Ctrl+C to stop waiting.\n", flush=True)
    try:
        while True:
            info = get_session_info()
            if info:
                cur_status = info.get("status")
                phone = info.get("phone")
                if cur_status in ["WORKING", "authenticated", "ready"] or phone:
                    print("\n🎉 CONGRATULATIONS! WhatsApp connected successfully!", flush=True)
                    print(f"Connected Account: {info.get('pushName')} ({phone})", flush=True)
                    print("FarmAssist is now live on WhatsApp and listening for farmer questions!\n", flush=True)
                    break
                else:
                    print(f"[Status]: {cur_status}... (waiting for scan)", end="\r", flush=True)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nProcess stopped. OpenWA container continues running in background.", flush=True)

if __name__ == "__main__":
    main()
