from fastapi import FastAPI

app = FastAPI(title="Deadlock Lab API")


@app.get("/health")
def health():
    return {"status": "ok"}