import io
import os
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, HTTPException, Form, File
import boto3
from botocore.exceptions import NoCredentialsError
import json
from PIL import Image
import uuid

app = FastAPI(title="Analyzer",
    description="Image Detection API",
    version="0.1.1",
    openapi_url="/api/v0.1.1/openapi.json",
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
S3_BUCKET_UPLOAD = "aiathelp"
Table = 'aiathelp'


s3 = boto3.client('s3',
                  aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY, region_name='us-east-1')
dynamodb = boto3.client('dynamodb', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY,
                        region_name='us-east-1')

def resize_image(image_file):
    image = Image.open(image_file.file)
    image.thumbnail((512, 512))
    image_file.file = image
    return image_file

def rename_image(image_file, username):
    # Making image name as UUID.jpg or UUID.png based on the image type
    image_name = str(username+"_"+str(uuid.uuid4()))
    image_type = image_file.filename.split(".")[-1]
    image_file.filename = f"{image_name}.{image_type}"


@app.get("/")
def index():
    return {"message": "Hello User!"}

@app.get("/list/")
async def read_root():
    try:
        lists = s3.list_buckets()
        bucket_names = [x["Name"] for x in lists["Buckets"]]
        return {"message": "List of S3 buckets", "buckets": bucket_names}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not configured")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def resize_image(image_file, max_file_size_kb=100):
    try:
        with Image.open(io.BytesIO(image_file.file.read())) as img:
            img.thumbnail((800, 800))

            buffer = io.BytesIO()
            img.save(buffer, format='JPEG')

            file_size_kb = len(buffer.getvalue()) / 1024
            if file_size_kb > max_file_size_kb:
                raise HTTPException(status_code=400, detail="Resized image exceeds size limit")

            buffer.seek(0)
            return buffer
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resizing image: {str(e)}")

def rename_image(image_file, username):
    image_name = str(username + "_" + str(uuid.uuid4()))
    image_type = image_file.filename.split(".")[-1]
    image_file.filename = f"{image_name}.{image_type}"

@app.post("/upload/")
async def upload_file(image_file: UploadFile = File(...), username: str = Form(...)):
    try:
        if not image_file or image_file.filename == "":
            raise HTTPException(status_code=400, detail="No image file provided")

        # Check if the file is an image
        if not image_file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File provided is not an image")

        # Resize the image
        resized_image = resize_image(image_file)

        # Rename the image (if needed)
        rename_image(image_file, username)

        s3_key = f"{username}/{image_file.filename}"
        s3.upload_fileobj(
            Fileobj=resized_image,
            Bucket=S3_BUCKET_UPLOAD,
            Key=s3_key,
        )

        return {"message": "File uploaded successfully"}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/")
async def get_user_data(username: str = Form(...)):

    try:
        gettabledata = dynamodb.get_item(TableName=Table, Key={'Username': {'S': username}})
        if 'Item' not in gettabledata:
            raise HTTPException(status_code=404, detail="User data not found")

        else:
            userdata = gettabledata['Item']
            userdata = json.loads(userdata.get('Data', {'S': '[]'})['S'])
            return {"message": "User data found", "data": userdata}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

if __name__ == "__main__":
     import uvicorn
     uvicorn.run(app, port=os.getenv('PORT', 8000), host=os.getenv('HOST', '0.0.0.0'))


#OPENAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Analyzer",
        version="0.1.1",
        description="Image Detection API",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# This will generate the OpenAPI schema when you run the app using uvicorn.

