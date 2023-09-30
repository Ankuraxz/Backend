import os
import boto3
import uuid
from io import BytesIO
from datetime import datetime
import json
import urllib3
import uuid

# Initialize AWS clients using environment variables
aws_access_key_id = os.environ['AWS_ACCESS']
aws_secret_access_key = os.environ['AWS_SECRET']
aws_region = "us-east-1"
novu_key = os.environ['NOVU_KEY']

s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,
                  region_name=aws_region)
rekognition = boto3.client('rekognition', aws_access_key_id=aws_access_key_id,
                           aws_secret_access_key=aws_secret_access_key, region_name=aws_region)
dynamodb = boto3.client('dynamodb', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,
                        region_name=aws_region)

# EMAIL
sender_email = 'gurnoorsb68@gmail.com'
recipient_email = 'ankurvermaaxz@gmail.com'


def handler(event, context):
    bucket_name = 'aiathelp'
    new_bucket_name = 'aiathelpfetch'
    print(event)
    image_key = event['Records'][0]['s3']['object']['key']

    # Extract the username from the S3 key
    username = extract_username_from_key(image_key)
    print(f'Username is {username}')
    print(f'Key is {image_key}')

    # Resize the image and send it to Rekognition
    image = s3.get_object(Bucket=bucket_name, Key=image_key)
    image_data = image['Body'].read()
    resized_image_data = image_data
    # Process the resized image with Rekognition
    rekognition_response = rekognition.detect_labels(Image={'Bytes': resized_image_data})
    # print(f'Recognition Success, response is {rekognition_response}')

    # Extract labels and their confidence
    labels_and_confidence = [
        {'LabelName': label['Name'], 'Confidence': label['Confidence']}
        for label in rekognition_response['Labels']
    ]
    print(f'Labels and confidence: {labels_and_confidence}')

    # Upload the resized image to the new S3 bucket
    new_image_key = f'{username}/{uuid.uuid4()}.jpg'
    s3.put_object(Bucket=new_bucket_name, Key=new_image_key, Body=resized_image_data)
    print(f'Bucket Put success for user {username}')

    dynamo_data = {
        'UUID': str(uuid.uuid4()),
        'Username': username,
        'Link': f's3://{new_bucket_name}/{new_image_key}',
        'Results': {
            'labels': labels_and_confidence
        },
        'Datetime': str(datetime.now())
    }

    existing_item = dynamodb.get_item(TableName='aiathelp', Key={'Username': {'S': username}})

    if 'Item' in existing_item:
        existing_item = existing_item['Item']
        existing_data_str = existing_item.get('Data', {'S': '[]'})['S']
        existing_data = json.loads(existing_data_str)
        existing_data.append(dynamo_data)

        data_json = json.dumps(existing_data)

        dynamodb.update_item(
            TableName='aiathelp',
            Key={'Username': {'S': username}},
            UpdateExpression='SET #Data = :data',
            ExpressionAttributeNames={'#Data': 'Data'},
            ExpressionAttributeValues={':data': {'S': data_json}}  # Store JSON as a string in DynamoDB
        )

        print(f'Appended successfully in Dynamo for {username}')
    else:
        dynamo_data_list = [dynamo_data]
        data_json = json.dumps(dynamo_data_list)
        dynamodb.put_item(
            TableName='aiathelp',
            Item={'Username': {'S': username}, 'Data': {'S': data_json}}
        )
        print(f'Added successfully in Dynamo for {username}')

    print("Sending out Mail")
    response = email_service(username, dynamo_data)
    if response.status == 200:
        print("Request was successful!")
    else:
        print(f"Request failed with status code {response.status}:")


# Define a function to extract the username from the S3 key
def extract_username_from_key(image_key):
    parts = image_key.split('/')
    if len(parts) >= 2:
        return parts[0]
    else:
        return None


def email_service(username, payload):
    reciever = str(username) + "@gmail.com"
    url = 'https://api.novu.co/v1/events/trigger'
    headers = {
        'Authorization': 'ApiKey ' + novu_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    # Define the request data as a dictionary
    data = {
        "name": "emailerworkflow",
        "to": {
            "subscriberId": str(uuid.uuid4()),
            "email": reciever
        },
        "payload": {'Results': json.dumps(payload)}
    }

    # Send the POST request
    http = urllib3.PoolManager()
    encoded_data = json.dumps(data).encode('utf-8')
    response = http.request('POST', url, headers=headers, body=encoded_data)

    return response



