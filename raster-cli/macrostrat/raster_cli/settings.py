from dotenv import load_dotenv
from os import getenv

load_dotenv()

S3_BUCKET_NAME = getenv("S3_BUCKET_NAME")
S3_ACCESS_KEY = getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = getenv("S3_SECRET_KEY")
S3_ENDPOINT_URL = getenv("S3_ENDPOINT_URL", None)
