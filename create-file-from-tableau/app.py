import json
import logging
import os
from urllib import parse

import boto3
from botocore.exceptions import ClientError
from tableau_api_lib import TableauServerConnection as tsc
from tableau_api_lib.utils import querying, flatten_dict_column


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLEAU_SECRET_NAME = os.environ.get('TABLEAU_SECRET_NAME')


def get_secrets_tableau():
    """
        Retrieves secrets for Test.
    """
    logger.info('Attepting to retrieve secrets for %s' % TABLEAU_SECRET_NAME)
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')
    
    try:
        secrets_response = client.get_secret_value(SecretId=TABLEAU_SECRET_NAME)
        secrets = json.loads(secrets_response['SecretString'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            raise e
            
    return secrets

def tableau_connection(secrets):
    logger.info('Connecting to Tableau')
    config = {
        'tableau_online': {
            'server': secrets['server'],
            'api_version': secrets['api_version'],
            'username': secrets['username'] , 
            'password': secrets['password'] ,  
            'site_name': secrets['site_name'],
            'site_url': secrets['site_url'],
        }
    }
    connection = tsc(config_json=config, env='tableau_online')
    response = connection.sign_in()
    return connection

def generate_pdf_params(tableau_params):
    logger.info('Generating Tableau View Params')
    pdf_settings = tableau_params.get("pdf_settings")
    dashboard_filters = tableau_params.get("dashboard_filters")
    layout = {
        "pdf_layout": f'type={pdf_settings.get("type")}',
        "pdf_orientation": f'orientation={pdf_settings.get("orientation")}'
    }
    filters = {}

    for i, (k, v) in enumerate(dashboard_filters.items()):
        filters[f'filter_{i}']=f'vf_{parse.quote(k)}={parse.quote(v)}'

    view_params = {**layout,**filters}
    logger.info('view params that will be used: %s', view_params)
    return view_params

def obtain_view_id(tableau_connection, view_tableau_name):
    logger.info('Obtaining view id from: %s', view_tableau_name)
    views_df = flatten_dict_column(querying.get_views_dataframe(tableau_connection), keys=["name","id"], col_name="workbook")
    pdf_view_id = views_df.loc[views_df['viewUrlName'] == view_tableau_name, 'id'].values[0]
    return pdf_view_id

def obtain_workbook_id(tableau_connection, workbook_tableau_name):
    logger.info('Obtaining workbook id from: %s', workbook_tableau_name)
    workbooks_df = querying.get_workbooks_dataframe(tableau_connection)
    pdf_workbook_id = workbooks_df.loc[workbooks_df['name']== workbook_tableau_name,'id'].values[0]
    return pdf_workbook_id

def upload_to_s3(bucket_name, object_name, pdf):
    logger.info('Attempting to load PDF to S3')
    session = boto3.Session()
    s3 = session.resource('s3')
    object = s3.Object(bucket_name, object_name)
    result = object.put(Body = pdf.content)

def tableau_view_pdf_to_s3(connection, file_from, tableau_name, bucket_name, object_name, tableau_params=None):
    logger.info('PDF source: %s', file_from)
    logger.info('Creating PDF from: %s', tableau_name)
    
    if file_from == 'View':
        view_tableau_id = obtain_view_id(connection, tableau_name )
        pdf = connection.query_view_pdf(view_id=view_tableau_id, parameter_dict=tableau_params)
    elif file_from =='Workbook':
        workbook_tableau_id = obtain_workbook_id(connection,tableau_name)
        pdf = connection.download_workbook_pdf(workbook_id=workbook_tableau_id, parameter_dict=tableau_params)
    else:
        logger.info(f'PDF source: {file_from} invalid, please select between View or Workbook')

    upload_to_s3(bucket_name, object_name, pdf)
    
def lambda_handler(event, _):
    file_from = event.get('file_from')
    tableau_name = event.get('tableau_name')
    bucket_name = event.get('bucket_name')
    object_name = event.get('object_name')
    tableau_params = event.get('tableau_params')

    try:
        view_params = generate_pdf_params(tableau_params) 
        tableau_credentials = get_secrets_tableau()
        connection = tableau_connection(tableau_credentials)
        tableau_view_pdf_to_s3(connection, file_from, tableau_name, bucket_name, object_name, view_params)  
        connection.sign_out()
        logger.info('PDF '+ object_name +' uploaded to S3!')
        return {
            'status_code': 200
        }
    except Exception as err:
        logger.error('Unexpected error: %s', err)
        return {
            'status_code': 500,
            'message': err
        }        