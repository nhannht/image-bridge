"""Image Bridge — lightweight image paste/upload server."""
import argparse
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn

DEFAULT_UPLOAD_DIR = Path(__file__).parent.parent / "uploads"


def create_app(upload_dir: Path = DEFAULT_UPLOAD_DIR) -> FastAPI:
    upload_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Image Bridge", version="0.1.0")

    @app.post("/upload")
    async def upload(file: UploadFile = File(...)):
        ext = file.filename.split(".")[-1] if "." in (file.filename or "") else "png"
        name = f"{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"
        path = upload_dir / name
        data = await file.read()
        path.write_bytes(data)
        return JSONResponse({
            "path": str(path.resolve()),
            "filename": name,
            "size": len(data),
        })

    @app.get("/uploads/{filename}")
    async def serve_upload(filename: str):
        path = (upload_dir / filename).resolve()
        if not str(path).startswith(str(upload_dir.resolve())):
            return JSONResponse({"error": "forbidden"}, status_code=403)
        if not path.exists() or not path.is_file():
            return JSONResponse({"error": "not found"}, status_code=404)
        return FileResponse(path)

    @app.get("/api/images")
    async def list_images():
        files = sorted(upload_dir.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
        return [
            {"filename": f.name, "path": str(f.resolve()), "size": f.stat().st_size}
            for f in files if f.is_file()
        ]

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return (Path(__file__).parent.parent / "static" / "index.html").read_text()

    return app


def cli():
    parser = argparse.ArgumentParser(description="Image Bridge server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=9876, help="Port")
    parser.add_argument("--upload-dir", type=Path, default=DEFAULT_UPLOAD_DIR)
    args = parser.parse_args()
    app = create_app(args.upload_dir)
    uvicorn.run(app, host=args.host, port=args.port)


app = create_app()

if __name__ == "__main__":
    cli()
