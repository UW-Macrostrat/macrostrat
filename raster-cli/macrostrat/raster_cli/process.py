from contextlib import contextmanager
from os import path
from pathlib import Path
from subprocess import run
from urllib.parse import urlparse
from uuid import uuid4
from zipfile import ZipFile, is_zipfile

import rasterio
import wget
from boto3.session import Session
from rasterio.errors import RasterioIOError
from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles

from .settings import S3_ACCESS_KEY, S3_BUCKET_NAME, S3_ENDPOINT_URL, S3_SECRET_KEY


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
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )
    s3 = session.client("s3", endpoint_url=S3_ENDPOINT_URL)
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
        **options,
    )
    return True


@contextmanager
def tempfile(extension=None):
    """Create a temporary file."""
    name = str(uuid4())
    if extension:
        name += extension
    name = path.join("/tmp", name)
    try:
        yield name
    finally:
        Path(name).unlink(missing_ok=True)


def process_image(
    url,
    out_key=None,
    profile="lzw",
    profile_options={},
    copy_valid_cog=True,
    **options,
) -> str:
    """Download, convert and upload."""
    url = url.strip()
    url_info = urlparse(url)
    filepath = Path(url_info.path)
    ext = "".join(filepath.suffixes)

    out_key = out_key or filepath.stem
    if not out_key.endswith(".tif"):
        out_key += ".tif"

    print(f"Processing {url} to {out_key}")

    with tempfile(extension=ext) as src_path, tempfile(extension=".tif") as dst_path:
        if url_info.scheme.startswith("http"):
            wget.download(url, src_path)
        elif url_info.scheme == "s3":
            _s3_download(url, src_path)
        elif filepath.exists():
            src_path = url
        else:
            raise Exception(f"Unsuported scheme {url_info.scheme}")

        should_copy = copy_valid_cog
        rio_openable = None
        # Use the appropriate GDAL VSI driver for zip files
        if url.endswith(".zip") or is_zipfile(src_path):
            zip_path = "/vsizip/" + path.abspath(src_path)
            # Check if RasterIO can read the zip file directly
            try:
                rasterio.open(zip_path)
                rio_openable = zip_path
            except RasterioIOError:
                # If not, find the largest file in the zip and use that
                with ZipFile(src_path) as zf:
                    largest = sorted(zf.filelist, key=lambda x: x.file_size)[-1]
                    rio_openable = (
                        f"/vsizip/{path.abspath(src_path)}/{largest.filename}"
                    )

            should_copy = False
        elif url.endswith(".tar.gz"):
            rio_openable = "/vsitar/" + path.abspath(src_path)
            should_copy = False

        if rio_openable is None:
            rio_openable = src_path

        if should_copy:
            try:
                should_copy = cog_validate(rio_openable)
            except RasterioIOError:
                pass

        # This is not always available without a full GDAL install
        # RasterIO tools should be used instead.
        # run(["gdalinfo", src_path])

        if should_copy:
            dst_path = src_path
        else:
            print("Converting to COG")
            _translate(
                rio_openable,
                dst_path,
                profile=profile,
                profile_options=profile_options,
                **options,
            )

        _upload(dst_path, S3_BUCKET_NAME, out_key)

        return path.join(S3_ENDPOINT_URL, S3_BUCKET_NAME, out_key)
