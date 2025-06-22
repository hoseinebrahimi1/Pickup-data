from fastapi import FastAPI, Request, HTTPException
import subprocess
import sys
import os

# گرفتن مقدار کلید از محیط (تعریف‌شده در Render)
API_KEY = os.getenv("MY-API-KEY")  # چون تو Render این کلیدو به اسم MY-API-KEY ذخیره کردی

app = FastAPI()

# تابع اعتبارسنجی
def verify_api_key(request: Request):
    client_key = request.headers.get("X-API-Key")
    if client_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.get("/ping")
async def ping():
    return {"pong": "ok"}

@app.post("/run/roja")
async def run_roja(request: Request):
    verify_api_key(request)
    p = subprocess.run(
        [sys.executable, "roja_shop_data.py"],
        capture_output=True,
        text=True
    )
    return {
        "stdout": p.stdout,
        "stderr": p.stderr,
        "returncode": p.returncode
    }

@app.post("/run/khanoumi")
async def run_khanoumi(request: Request):
    verify_api_key(request)
    p = subprocess.run(
        [sys.executable, "khanoumi_data.py"],
        capture_output=True,
        text=True
    )
    return {
        "stdout": p.stdout,
        "stderr": p.stderr,
        "returncode": p.returncode
    }
