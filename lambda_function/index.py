import os
import boto3
import uuid
from datetime import datetime
import json

aws_access_key_id = os.environ['AWS_ACCESS']
aws_secret_access_key = os.environ['AWS_SECRET']
aws_region = "us-east-1"

s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,
                  region_name=aws_region)
rekognition = boto3.client('rekognition', aws_access_key_id=aws_access_key_id,
                           aws_secret_access_key=aws_secret_access_key, region_name=aws_region)
dynamodb = boto3.client('dynamodb', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key,
                        region_name=aws_region)


def handler(event, context):
    bucket_name = 'aiathelp'
    new_bucket_name = 'aiathelpfetch'
    print(event)
    image_key = event['Records'][0]['s3']['object']['key']
    username = extract_username_from_key(image_key)
    print(f'Username is {username}')

    image = s3.get_object(Bucket=bucket_name, Key=image_key)
    image_data = image['Body'].read()
    resized_image_data = image_data

    rekognition_response = rekognition.detect_labels(Image={'Bytes': resized_image_data})

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
        'Results':  {
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
                    ExpressionAttributeValues={':data': {'S': data_json}}
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

def extract_username_from_key(image_key):
    parts = image_key.split('/')
    if len(parts) >= 2:
        return parts[0]
    else:
        return None

