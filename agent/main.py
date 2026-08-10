import httpx
import sys
import os

from dotenv import load_dotenv
load_dotenv()

url = os.getenv("ORCHESTRATOR_URL")
print(url)
try:
    r = httpx.get(url + "/health", timeout = 15)
    if r.status_code == 200:
        print("Orchestrator Healthy")
        sys.exit(0)
    else:
        print("Orchestrator Reachable but Unhealthy",r.status_code)
        sys.exit(1)
except httpx.RequestError as e:
    print("Down", e)
    sys.exit(1)
