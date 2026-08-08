"""Drive live BlenderMCP socket from terminal on Windows."""
import json, socket, sys, time

HOST, PORT = "127.0.0.1", 9876

def send(cmd, params=None, timeout=60.0):
    params = params or {}
    s = socket.socket(); s.settimeout(timeout); s.connect((HOST, PORT))
    s.sendall(json.dumps({"type": cmd, "params": params}).encode())
    out = b""; deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            chunk = s.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        out += chunk
        try:
            return json.loads(out.decode())
        except json.JSONDecodeError:
            continue
    s.close()
    try:
        return json.loads(out.decode())
    except Exception:
        return {"status": "error", "message": f"bad response: {out[:300]}"}

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "scene"
    if action == "code":
        r = send("execute_code", {"code": sys.argv[2]}, timeout=float(sys.argv[3]) if len(sys.argv) > 3 else 60)
    elif action == "screenshot":
        r = send("get_viewport_screenshot", {"filepath": sys.argv[2], "max_size": 900})
    elif action == "scene":
        r = send("get_scene_info")
    elif action == "hyper3d_status":
        r = send("get_hyper3d_status")
    elif action == "rodin_job":
        r = send("create_rodin_job", {"text_prompt": sys.argv[2]}, timeout=300)
    elif action == "rodin_poll":
        r = send("poll_rodin_job_status", {"subscription_key": sys.argv[2]}, timeout=60)
    elif action == "rodin_import":
        r = send("import_generated_asset", {"name": sys.argv[2], "task_uuid": sys.argv[3]}, timeout=180)
    else:
        r = {"status": "error", "message": f"unknown: {action}"}
    print(json.dumps(r, indent=2)[:2500])
