import os
import uuid
import logging
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, HTTPException
import boto3
from botocore.client import Config

router = APIRouter(
    prefix="/image_upload",
    tags=["s3"],
    responses={404: {"description": "Image upload not found"}},
)

load_dotenv()

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PATH = os.getenv("S3_PATH", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    config=Config(
        request_checksum_calculation='WHEN_REQUIRED',
        response_checksum_validation='WHEN_REQUIRED',
    )
)

@router.post("")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_content = await file.read()

        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty")

        new_filename = f"{uuid.uuid4()}-{file.filename}"
        s3_key = f"{S3_PATH.strip('/')}/{new_filename}" if S3_PATH else new_filename

        # Upload the file 
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,  
            ContentType=file.content_type or "application/octet-stream",
            ContentLength=len(file_content)  
        )

        file_url = f"{S3_ENDPOINT}/{S3_BUCKET}/{s3_key}"

        return {
            "filename": new_filename,
            "url": file_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
