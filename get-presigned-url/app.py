import logging

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_url_s3(bucket_name, object_name):
    logger.info('Attempting to get url: %s', object_name)
    url = boto3.client('s3').generate_presigned_url(
        ClientMethod = 'get_object',
        Params = {'Bucket': bucket_name,'Key': object_name},
        ExpiresIn = 600000 #seconds
        )
    return url

def lambda_handler(event, _):
    bucket_name = event.get('bucket_name','')
    object_name = event.get('object_name','')

    try:
        url = get_url_s3(bucket_name, object_name)
        logger.info('Generated PDF URL: %s',url)
        return {
            'status_code': 200,
            'results': url
        }
    except Exception as err:
        logger.error('Unexpected error: %s', err)
        return {
            'status_code': 500,
            'message': err
        }