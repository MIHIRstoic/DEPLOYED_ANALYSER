import os
import shutil

from fastapi import HTTPException, UploadFile, status

UPLOADS_DIR = "uploads"
ALLOWED_CONTENT_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


def validate_pdf(file: UploadFile) -> None:
    """
    Raises HTTPException(400) if:
    - content-type is not application/pdf
    - filename extension is not .pdf
    - file is empty (size = 0)
    """
    # Check content-type header
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Only PDF files are accepted.",
        )

    # Check file extension
    if file.filename:
        _, ext = os.path.splitext(file.filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension '{ext}'. Only .pdf files are accepted.",
            )

    # Check file is not empty
    if file.size is not None and file.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )


async def save_temp_file(file: UploadFile) -> str:
    """
    Saves the uploaded file to the local uploads/ directory.
    Creates the directory if it does not exist.
    Returns the absolute path to the saved file.
    """
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    safe_filename = os.path.basename(file.filename or "upload.pdf")
    dest_path = os.path.join(UPLOADS_DIR, safe_filename)

    # If a file with the same name already exists, prefix with a unique counter
    base, ext = os.path.splitext(safe_filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(UPLOADS_DIR, f"{base}_{counter}{ext}")
        counter += 1

    # Reset file cursor to start before reading
    await file.seek(0)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return os.path.abspath(dest_path)
