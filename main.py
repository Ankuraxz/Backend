from flask import Flask, request

import boto3

awstest2 = Flask(__name__)

try:
    s3 = boto3.client('s3')
    lists = s3.list_buckets()
    for x in lists["Buckets"]:
        print(f'Bucket name is {x["Name"]}')
except Exception as e:
    print(f'An error occurred: {str(e)}')

bucket_name = 'aiathelp'

@awstest2.post('/upload-images')
def upload_image():
    try:
        image_file = request.files['images']

        if image_file:
            object_key = 'imagestest/image.jpg'
            s3.upload_fileobj(
                Fileobj=image_file,
                Bucket=bucket_name,
                Key=object_key,
            )

            return {'message': ' Image successfully uploaded'}
        else:
            return {'error': 'No image file'}, 400
    except Exception as e:
        return {'error': str(e)}, 500

awstest2.run()
