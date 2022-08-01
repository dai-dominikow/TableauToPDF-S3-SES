import logging

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def send_url_email(url, email_sender, email_receiver, subject,message):
    logger.info('Attempting to send mail to : %s'+ email_receiver)
    ses_client = boto3.client("ses", region_name="us-west-2")
    CHARSET = "UTF-8"
    response = ses_client.send_email(
        Destination={
            "ToAddresses": [
                email_receiver,
            ],
        },
        Message={
            "Body": {
                "Text": {
                    "Charset": CHARSET,
                    "Data":
                        message +'\n' 
                        "Here's a link to your PDF report: \n"+
                        "Remember it's valid for only 48 hours!. \n \n \n" +
                        url + '\n \n \n' +
                        "This is an automated message, please do not respond to this email. If anything, feel free to contact the Analytics team." 
                     ,
                }
            },
            "Subject": {
                "Charset": CHARSET,
                "Data": subject,
            },
        },
        Source = email_sender, 
    )

def lambda_handler(event, _):
    emails = event.get('emails')
    email_sender = event.get('email_sender')
    url = event.get('url','')
    subject = event.get('subject','Dragonite has a message for you!')
    message = event.get('message','')

    try:
        [send_url_email(url, email_sender, email, subject, message) for email in emails] 
        logger.info('Mail delivered!')
        return {
            'status_code': 200
        }
    except Exception as err:
        logger.error('Unexpected error: %s', err)
        return {
            'status_code': 500,
            'message': err
        }