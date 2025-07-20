from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import os

router = APIRouter()

MODEL_DIR = "./forecast_model"
os.makedirs(MODEL_DIR, exist_ok=True)

@router.post("/upload-model/")
async def upload_model(file: UploadFile = File(...)):
    """
    Upload a retrained model file and store it in the MODEL_DIR.
    """
    try:
        file_path = Path(MODEL_DIR) / file.filename
        with open(file_path, "wb") as f:
            f.write(await file.read())

        return JSONResponse(status_code=200, content={
            "message": f"✅ Model '{file.filename}' uploaded successfully."
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Failed to upload model: {str(e)}")
