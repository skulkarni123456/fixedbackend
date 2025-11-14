import os
import uuid
import shutil
import subprocess
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.utils.files import save_upload_to_file, cleanup_paths, ensure_dir

router = APIRouter()

# Helper to run shell commands
def run_cmd(cmd):
    proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout, proc.stderr

@router.post("/word2pdf")
async def word2pdf(file: UploadFile = File(...)):
    # Uses LibreOffice (soffice) in headless mode
    in_path = await save_upload_to_file(file)
    out_dir = os.path.dirname(in_path)
    out_name = f"{uuid.uuid4().hex}.pdf"
    out_path = os.path.join(out_dir, out_name)
    # soffice command to convert
    cmd = f"soffice --headless --convert-to pdf --outdir {out_dir} {in_path}"
    code, out, err = run_cmd(cmd)
    # LibreOffice writes file with same basename but .pdf extension
    converted = os.path.splitext(in_path)[0] + ".pdf"
    if code != 0 or not os.path.exists(converted):
        cleanup_paths([in_path, converted])
        raise HTTPException(status_code=500, detail=f"conversion failed: {err or out}")
    shutil.move(converted, out_path)
    cleanup_paths([in_path])
    return FileResponse(out_path, filename="converted.pdf", media_type="application/pdf")

@router.post("/merge")
async def merge(files: list[UploadFile] = File(...)):
    # Save all files, then merge using PyPDF2
    saved = []
    for f in files:
        p = await save_upload_to_file(f)
        saved.append(p)
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    try:
        for p in saved:
            merger.append(p)
        out_path = os.path.join(os.path.dirname(saved[0]), f"{uuid.uuid4().hex}_merged.pdf")
        merger.write(out_path)
        merger.close()
    except Exception as e:
        merger.close()
        cleanup_paths(saved)
        raise HTTPException(status_code=500, detail=str(e))
    cleanup_paths(saved)
    return FileResponse(out_path, filename="merged.pdf", media_type="application/pdf")

@router.post("/split")
async def split(file: UploadFile = File(...)):
    p = await save_upload_to_file(file)
    from PyPDF2 import PdfReader, PdfWriter
    reader = PdfReader(p)
    out_files = []
    try:
        for i in range(len(reader.pages)):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            out_path = os.path.join(os.path.dirname(p), f"{uuid.uuid4().hex}_page_{i+1}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
            out_files.append(out_path)
    except Exception as e:
        cleanup_paths([p]+out_files)
        raise HTTPException(status_code=500, detail=str(e))
    # If only one page, return that file. Otherwise zip them.
    if len(out_files) == 1:
        cleanup_paths([p])
        return FileResponse(out_files[0], filename="page1.pdf", media_type="application/pdf")
    # create zip
    import zipfile
    zip_path = os.path.join(os.path.dirname(p), f"{uuid.uuid4().hex}_pages.zip")
    with zipfile.ZipFile(zip_path, "w") as z:
        for fp in out_files:
            z.write(fp, os.path.basename(fp))
    cleanup_paths([p]+out_files)
    return FileResponse(zip_path, filename="pages.zip", media_type="application/zip")

@router.post("/compress")
async def compress(file: UploadFile = File(...)):
    p = await save_upload_to_file(file)
    # Use ghostscript if available
    out_path = os.path.join(os.path.dirname(p), f"{uuid.uuid4().hex}_compressed.pdf")
    cmd = f"gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH -sOutputFile={out_path} {p}"
    code, out, err = run_cmd(cmd)
    if code != 0 or not os.path.exists(out_path):
        cleanup_paths([p, out_path])
        raise HTTPException(status_code=500, detail=f"compress failed: {err or out}")
    cleanup_paths([p])
    return FileResponse(out_path, filename="compressed.pdf", media_type="application/pdf")

@router.post("/pdf2jpg")
async def pdf2jpg(file: UploadFile = File(...)):
    p = await save_upload_to_file(file)
    # uses pdf2image
    from pdf2image import convert_from_path
    pages = convert_from_path(p)
    out_paths = []
    try:
        for i, img in enumerate(pages):
            out_path = os.path.join(os.path.dirname(p), f"{uuid.uuid4().hex}_page_{i+1}.jpg")
            img.save(out_path, "JPEG")
            out_paths.append(out_path)
    except Exception as e:
        cleanup_paths([p]+out_paths)
        raise HTTPException(status_code=500, detail=str(e))
    # if single image return it, else zip
    if len(out_paths) == 1:
        cleanup_paths([p])
        return FileResponse(out_paths[0], filename="page1.jpg", media_type="image/jpeg")
    import zipfile
    zip_path = os.path.join(os.path.dirname(p), f"{uuid.uuid4().hex}_jpgs.zip")
    with zipfile.ZipFile(zip_path, "w") as z:
        for fp in out_paths:
            z.write(fp, os.path.basename(fp))
    cleanup_paths([p]+out_paths)
    return FileResponse(zip_path, filename="pages.zip", media_type="application/zip")

@router.post("/jpg2pdf")
async def jpg2pdf(file: UploadFile = File(...)):
    p = await save_upload_to_file(file)
    # if upload is multiple images, FastAPI needs list; here we accept a single image and convert
    from PIL import Image
    img = Image.open(p)
    out_path = os.path.join(os.path.dirname(p), f"{uuid.uuid4().hex}_img2pdf.pdf")
    img.convert("RGB").save(out_path, "PDF", resolution=100.0)
    cleanup_paths([p])
    return FileResponse(out_path, filename="img2pdf.pdf", media_type="application/pdf")

@router.post("/protect")
async def protect(file: UploadFile = File(...), password: str = "secret"):
    p = await save_upload_to_file(file)
    # uses qpdf
    out_path = os.path.join(os.path.dirname(p), f"{uuid.uuid4().hex}_protected.pdf")
    cmd = f"qpdf --encrypt {password} {password} 256 -- {p} {out_path}"
    code, out, err = run_cmd(cmd)
    if code != 0 or not os.path.exists(out_path):
        cleanup_paths([p, out_path])
        raise HTTPException(status_code=500, detail=f"protect failed: {err or out}")
    cleanup_paths([p])
    return FileResponse(out_path, filename="protected.pdf", media_type="application/pdf")

@router.post("/unlock")
async def unlock(file: UploadFile = File(...), password: str = "secret"):
    p = await save_upload_to_file(file)
    out_path = os.path.join(os.path.dirname(p), f"{uuid.uuid4().hex}_unlocked.pdf")
    cmd = f"qpdf --password={password} --decrypt {p} {out_path}"
    code, out, err = run_cmd(cmd)
    if code != 0 or not os.path.exists(out_path):
        cleanup_paths([p, out_path])
        raise HTTPException(status_code=500, detail=f"unlock failed: {err or out}")
    cleanup_paths([p])
    return FileResponse(out_path, filename="unlocked.pdf", media_type="application/pdf")