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


# Create the FastAPI app
app = FastAPI(title="Analyzer",
    description="Image Detection API",
    version="0.1.1",
    openapi_url="/api/v0.1.1/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Load environment variables
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
S3_BUCKET_UPLOAD = "aiathelp"
Table = 'aiathelp'


# Create the S3 and DynamoDB clients
s3 = boto3.client('s3',
                  aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY, region_name='us-east-1')

dynamodb = boto3.client('dynamodb', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY,
                        region_name='us-east-1')

def resize_image(image_file, max_file_size_kb=100):
    """
    Resize the image to a maximum file size (in KB)
    :param image_file: The image file to resize
    :param max_file_size_kb: The maximum file size (in KB) to resize to
    :return: The resized image file
    """
    try:
        with Image.open(io.BytesIO(image_file.file.read())) as img:
            img.thumbnail((800, 800))

            buffer = io.BytesIO()
            img = img.convert('RGB')
            img.save(buffer, format='JPEG')

            file_size_kb = len(buffer.getvalue()) / 1024
            if file_size_kb > max_file_size_kb:
                raise HTTPException(status_code=400, detail="Resized image exceeds size limit") from None

            buffer.seek(0)
            return buffer
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resizing image: {str(e)}") from e

def rename_image(image_file, username):
    """
    Rename the image file to a unique name in-place
    :param image_file: The image file to rename
    :param username: The username to use in the image name
    :return: None
    """
    image_name = str(username + "_" + str(uuid.uuid4()))
    image_type = image_file.filename.split(".")[-1]
    # if no type, default to jpg
    if len(image_type) == 0:
        image_type = "jpg"
    image_file.filename = f"{image_name}.{image_type}"

@app.get("/")
def index():
    return {"message": "Hello User!"}

@app.get("/lists/")
async def read_root():
    """
    List all S3 buckets
    :return: A list of all S3 buckets
    """
    try:
        lists = s3.list_buckets()
        bucket_names = [x["Name"] for x in lists["Buckets"]]
        return {"message": "List of S3 buckets", "buckets": bucket_names}
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="AWS credentials not configured")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e




@app.post("/upload/")
async def upload_file(image_file: UploadFile = File(...), username: str = Form(...)):
    """
    Upload a file to S3
    :param image_file: The image file to upload
    :param username: The username to use in the image name
    :return: A message indicating the file was uploaded successfully
    """
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
    """
    Get user data from DynamoDB
    :param username: The username to find in DynamoDB
    :return: User Data saved in DynamoDB whose username matches the provided username and confidence > 60
    """
    try:
        gettabledata = dynamodb.get_item(TableName=Table, Key={'Username': {'S': username}})
        if 'Item' not in gettabledata:
            raise HTTPException(status_code=404, detail="User data not found")

        else:

            userdata = gettabledata['Item']
            userdata = json.loads(userdata.get('Data', {'S': '[]'})['S'])
            for item in userdata:
                newlist = []
                x = item["Results"]["labels"]
                for items in x:
                    if items["Confidence"]>60:
                        newlist.append({'LabelName': items['LabelName'], 'Confidence': items['Confidence']})
                item["Results"]["labels"] = newlist

            print(userdata)
            return {"message": "User data found", "data": userdata}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

if __name__ == "__main__":
     import uvicorn
     uvicorn.run(app, port=os.getenv('PORT', 8000), host=os.getenv('HOST', '0.0.0.0'))


#OPENAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    """
    Customized OpenAPI schema
    """
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
#CI/CD pipeline