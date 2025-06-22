from fastapi import FastAPI
import subprocess
import sys
import os
API_KEY = os.getenv("MY_API_KEY")

app = FastAPI()

@app.get("/ping")
async def ping():
    return {"pong": "ok"}

@app.post("/run/roja")
async def run_roja():
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
async def run_khanoumi():
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
