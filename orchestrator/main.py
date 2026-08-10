from fastapi import FastAPI
import os
from dotenv import load_dotenv
import psycopg
from fastapi.responses import JSONResponse

load_dotenv()

app = FastAPI()



@app.get("/service")
def ping():
    return {"service":"orchestrator"}

@app.get("/health")
def health():
    url = os.getenv("DATABASE_URL")
    def status():
        with psycopg.connect(url, connect_timeout = 5) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()

    try:
         status()
         result = "working"
    except Exception:
         result = "Failed"

    if result == "working":
        return{"status":"ok", "db":"ok", "version":"0.1.0"}
    else:
         return JSONResponse(status_code=503, content={"status":"degraded","db": "down","version":"0.1.0"})

    
         
    

