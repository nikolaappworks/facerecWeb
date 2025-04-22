import os
from dotenv import load_dotenv
import json
import boto3
import logging
from botocore.exceptions import NoCredentialsError

# Koristite apsolutnu putanju do .env fajla
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
logger = logging.getLogger(__name__)
logger.info(f"Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path)

# Dodajte ove linije za debug
logger.info(f"S3_ACCESS_KEY_ID: {'*' * (len(os.getenv('S3_ACCESS_KEY_ID') or '') if os.getenv('S3_ACCESS_KEY_ID') else 'Not set')}")
logger.info(f"S3_SECRET_ACCESS_KEY: {'*' * (len(os.getenv('S3_SECRET_ACCESS_KEY') or '') if os.getenv('S3_SECRET_ACCESS_KEY') else 'Not set')}")
logger.info(f"S3_ENDPOINT: {os.getenv('S3_ENDPOINT') or 'Not set'}")
logger.info(f"S3_DEFAULT_REGION: {os.getenv('S3_DEFAULT_REGION') or 'Not set'}")

class WasabiService:
    @staticmethod
    def get_s3_client():
        # Direktno postavljanje kredencijala (samo za testiranje)
        access_key = os.getenv("S3_ACCESS_KEY_ID") or "vaš_access_key"
        secret_key = os.getenv("S3_SECRET_ACCESS_KEY") or "vaš_secret_key"
        endpoint = os.getenv("S3_ENDPOINT") or "https://s3.wasabisys.com"
        region = os.getenv("S3_DEFAULT_REGION") or "us-east-1"
        
        logger.info(f"Using S3 credentials - Access Key: {'*' * len(access_key)}, Endpoint: {endpoint}, Region: {region}")
        
        return boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint,
            region_name=region
        )
        
    @staticmethod
    def upload_to_s3(local_path, s3_bucket, s3_key):
        logger.info(f"Uploading {local_path} to S3 bucket: {s3_bucket}, key: {s3_key}")
        s3 = WasabiService.get_s3_client()
        try:
            s3.upload_file(local_path, s3_bucket, s3_key)
            logger.info(f"Successfully uploaded {local_path} to S3 as {s3_key}")
        except FileNotFoundError:
            logger.error(f"File not found: {local_path}")
            raise Exception(f"File not found: {local_path}")
        except NoCredentialsError:
            logger.error("S3 credentials not available.")
            raise Exception("S3 credentials not available.")
        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            raise Exception(f"Error uploading to S3: {str(e)}")