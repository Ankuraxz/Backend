import os
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, HTTPException, Form, File
import boto3
from botocore.exceptions import NoCredentialsError

app = FastAPI(title="Analyzer",
    description="Image Detection API",
    version="0.1.1",
    openapi_url="/api/v0.1.1/openapi.json",
    docs_url="/api/v0.1.1/docs",
    redoc_url="/api/v0.1.1/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
S3_ACCESS_POINT = os.getenv('S3_ACCESS_POINT')
S3_BUCKET_UPLOAD = "aiathelp"
Table = 'aiathelp'


#Create Clients
s3 = boto3.client('s3',
                  aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY,
                  endpoint_url=S3_ACCESS_POINT)
dynamodb = boto3.client('dynamodb', region_name='us-east-1')


@app.get("/list")
async def read_root():
    try:
        lists = s3.list_buckets()
        bucket_names = [x["Name"] for x in lists["Buckets"]]
        return {"message": "List of S3 buckets", "buckets": bucket_names}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not configured")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/upload/")
async def upload_file(image_file: Optional[UploadFile] = File(...),username: str = Form(...)):
    try:
        if not image_file or image_file.filename == "":
            raise HTTPException(status_code=400, detail="No image file provided")
        # check if file is image
        if not image_file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File provided is not an image")
        s3_key = f"{username}/{image_file.filename}"
        print(image_file)

        s3.upload_fileobj(
            Fileobj=image_file.file,
            Bucket=S3_BUCKET_UPLOAD,
            Key=s3_key,
        )

        return {"message": "File uploaded successfully"}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/user/")
async def get_user_data(username: str = Form(...)):
    try:
        gettabledata = dynamodb.get_item(
            TableName=table,
            Key={str(username): {'S': username}} ## Needs changes respective to the table
        )
        if 'Item' not in gettabledata:
            raise HTTPException(status_code=404, detail="User data not found")

        userdata = gettabledata['Item']
        print(userdata)
        return userdata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
