# config.py
import os
from dotenv import load_dotenv # type: ignore

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key'
    
    # Get environment setting
    environment = os.environ.get('ENVIRONMENT', 'local')
    
    if environment == 'production':
        # PythonAnywhere Database configuration
        DB_HOST = os.environ.get('PROD_DB_HOST')
        DB_USER = os.environ.get('PROD_DB_USER')
        DB_PASSWORD = os.environ.get('PROD_DB_PASSWORD')
        DB_NAME = os.environ.get('PROD_DB_NAME')
    else:
        # Local Database configuration
        DB_HOST = os.environ.get('LOCAL_DB_HOST')
        DB_USER = os.environ.get('LOCAL_DB_USER')
        DB_PASSWORD = os.environ.get('LOCAL_DB_PASSWORD')
        DB_NAME = os.environ.get('LOCAL_DB_NAME')
