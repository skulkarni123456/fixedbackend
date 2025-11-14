import os
import shutil
import aiofiles
import uuid

UPLOAD_DIR = "uploads"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

async def save_upload_to_file(upload_file):
    ensure_dir(UPLOAD_DIR)
    suffix = os.path.splitext(upload_file.filename)[1] or ""
    filename = f"{uuid.uuid4().hex}{suffix}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await upload_file.read()
        await out_file.write(content)
    return file_path

def cleanup_paths(paths):
    for p in paths:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                os.remove(p)
        except Exception:
            pass