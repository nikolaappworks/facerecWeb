from dotenv import load_dotenv
import os
import json
import boto3
import logging
from botocore.exceptions import NoCredentialsError

load_dotenv()

logger = logging.getLogger(__name__)

class WasabiService:
    @staticmethod
    def get_s3_client():
        return boto3.client(
            's3',
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
            endpoint_url=os.getenv("S3_ENDPOINT"),
            region_name=os.getenv("S3_DEFAULT_REGION")
        )
        
    def upload_to_s3(self, local_path, s3_bucket, s3_key):
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