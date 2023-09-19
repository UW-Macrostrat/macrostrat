from urllib.parse import urlparse

import wget
from uuid import uuid4
from contextlib import contextmanager
from boto3.session import Session
from pathlib import Path

from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles
from zipfile import ZipFile, is_zipfile

from .settings import S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_URL


def _s3_download(path, key):
    session = Session()
    s3 = session.client("s3")
    url_info = urlparse(path.strip())
    s3_bucket = url_info.netloc
    s3_key = url_info.path.strip("/")
    s3.download_file(s3_bucket, s3_key, key)
    return True


def _upload(path, bucket, key):
    session = Session(
        aws_access_key_id=S3_ACCESS_KEY, aws_secret_access_key=S3_SECRET_KEY
    )
    s3 = session.client("s3")
    with open(path, "rb") as data:
        s3.upload_fileobj(data, bucket, key)
    return True


def _translate(src_path, dst_path, profile="lzw", profile_options={}, **options):
    """Convert image to COG."""
    output_profile = cog_profiles.get(profile)
    output_profile.update(dict(BIGTIFF="IF_SAFER"))
    output_profile.update(profile_options)

    config = dict(
        GDAL_NUM_THREADS="ALL_CPUS",
        GDAL_TIFF_INTERNAL_MASK=True,
        GDAL_TIFF_OVR_BLOCKSIZE="128",
    )

    cog_translate(
        src_path,
        dst_path,
        output_profile,
        config=config,
        in_memory=False,
        quiet=True,
        **options,
    )
    return True


@contextmanager
def tempfile():
    name = str(uuid4())
    yield name
    Path(name).unlink()


def process_image(
    url,
    out_key=None,
    profile="lzw",
    profile_options={},
    copy_valid_cog=True,
    **options,
) -> str:
    """Download, convert and upload."""
    url_info = urlparse(url.strip())
    filename = url_info.path.split("/")[-1]
    out_key = out_key or filename
    if not out_key.endswith(".tif"):
        out_key += ".tif"

    with tempfile() as src_path, tempfile() as dst_path:
        if url_info.scheme.startswith("http"):
            wget.download(url, src_path)
        elif url_info.scheme == "s3":
            _s3_download(url, src_path)
        else:
            raise Exception(f"Unsuported scheme {url_info.scheme}")

        # Unzip if needed
        if is_zipfile(src_path):
            with ZipFile(src_path, "r") as zip_ref:
                # Get the largest file
                files = zip_ref.namelist()
                files.sort(key=lambda x: zip_ref.getinfo(x).file_size)
                _target = files[-1]
                zip_ref.extract(_target, src_path)
            src_path = src_path.replace(".zip", ".tif")

        if copy_valid_cog and cog_validate(src_path):
            dst_path = src_path
        else:
            _translate(
                src_path,
                dst_path,
                profile=profile,
                profile_options=profile_options,
                **options,
            )

        _upload(dst_path, S3_BUCKET_URL, out_key)

        return f"{S3_BUCKET_URL}/{out_key}"
