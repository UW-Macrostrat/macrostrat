from dotenv import load_dotenv
from os import getenv

load_dotenv()

S3_BUCKET_URL = getenv("S3_BUCKET_URL")
S3_ACCESS_KEY = getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = getenv("S3_SECRET_KEY")
