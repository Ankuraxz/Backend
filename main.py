import os
from fastapi import FastAPI, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, HTTPException, Form
from typing import Optional
import boto3
from botocore.exceptions import NoCredentialsError

app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all HTTP headers
)


AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
S3_ACCESS_POINT = os.getenv('S3_ACCESS_POINT')
S3_BUCKET = "aiathelp"

s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, endpoint_url=S3_ACCESS_POINT)

@app.get("/")
async def read_root():
    try:
        lists = s3.list_buckets()
        bucket_names = [x["Name"] for x in lists["Buckets"]]
        return {"message": "List of S3 buckets", "buckets": bucket_names}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not configured")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/")
async def upload_file(image_file: Optional[UploadFile] = File(...),username: str = Form(...)):
    try:
        if not image_file or image_file.filename == "":
            raise HTTPException(status_code=400, detail="No image file provided")

        # Generate the S3 key (path) where the file will be stored
        s3_key = f"{username}/{image_file.filename}"
        print(s3_key)  # Ensure that the s3_key is printed for debugging

        # Upload the file to S3
        s3.upload_fileobj(
            Fileobj=image_file.file,
            Bucket=S3_BUCKET,
            Key=s3_key,
        )

        return {"message": "File uploaded successfully"}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)