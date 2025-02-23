from fastapi import FastAPI, File, UploadFile, HTTPException
from utils import get_constructed_summary_and_keywords
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil

app = FastAPI()

#create temp pdf directory
UPLOAD_DIRECTORY = "pdfs"
os.makedirs(UPLOAD_DIRECTORY,exist_ok=True)

origins = [
    "http://localhost:3000",  #frontend's origin
    "http://localhost"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Receives the pdf and temporarily stores it
    processes it and returns summary and keyword
    """
    try:
        pdf_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        response_data = get_constructed_summary_and_keywords(pdf_path)
        os.remove(pdf_path)
        return {"response": response_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error : {str(e)}")