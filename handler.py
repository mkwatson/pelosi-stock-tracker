import hashlib
import logging
import os

import requests
from twilio.rest import Client
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def run(event, context):
    s3 = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    my_number = os.environ['MY_NUMBER']
    object_key = 'pelosi_stock_disclosure_hash.txt'

    # Fetch the current disclosure data
    response = requests.post(
        'https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult',
        data={'LastName': 'Pelosi', 'FilingYear': '2024', 'State': 'CA'}
    )
    current_data_hash = hashlib.md5(response.content).hexdigest()

    # Attempt to read the previous hash from S3
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        previous_data_hash = response['Body'].read().decode('utf-8')
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            previous_data_hash = None
        else:
            # Handle other possible exceptions (permissions, etc.)
            raise

    # Compare and update if a new disclosure is detected
    if current_data_hash != previous_data_hash:
        # Detected change, update the object in S3 with the new hash
        s3.put_object(Bucket=bucket_name, Key=object_key, Body=current_data_hash.encode('utf-8'))

        account_sid = os.environ['TWILIO_ACCOUNT_SID']
        auth_token = os.environ['TWILIO_AUTH_TOKEN']
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body="New Pelosi Trade! https://disclosures-clerk.house.gov/FinancialDisclosure",
            from_='whatsapp:+14155238886',
            to=f'whatsapp:{my_number}'
        )

    return {
        'statusCode': 200,
        'body': 'Process completed'
    }
