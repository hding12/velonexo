"""Verify configured Tigris and HF buckets using disposable text objects."""
import os
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('HF_HOME', str(Path(tempfile.gettempdir()) / 'velonexo-hf-cache'))
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
from dotenv import dotenv_values
import boto3
from botocore.config import Config
from huggingface_hub import batch_bucket_files, download_bucket_files


def probe_tigris(values, key, payload):
    client = boto3.client('s3', endpoint_url=values['TIGRIS_ENDPOINT_URL'],
        region_name=values['TIGRIS_REGION'], aws_access_key_id=values['TIGRIS_ACCESS_KEY_ID'],
        aws_secret_access_key=values['TIGRIS_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4', connect_timeout=10, read_timeout=20,
                      retries={'total_max_attempts': 2}, s3={'addressing_style': 'path'}))
    bucket = values['TIGRIS_BUCKET']
    print('tigris: uploading probe', flush=True)
    client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType='text/plain')
    print('tigris: upload PASS; reading probe', flush=True)
    try:
        with client.get_object(Bucket=bucket, Key=key)['Body'] as body:
            if body.read() != payload:
                raise ValueError('Downloaded content mismatch')
    finally:
        client.delete_object(Bucket=bucket, Key=key)


def probe_hf(values, key, payload):
    bucket, token = values['HF_BUCKET'], values['HF_TOKEN']
    batch_bucket_files(bucket, add=[(payload, key)], token=token)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'probe.txt'
            download_bucket_files(bucket, [(key, target)], token=False)
            if target.read_bytes() != payload:
                raise ValueError('Downloaded content mismatch')
    finally:
        batch_bucket_files(bucket, delete=[key], token=token)


def main():
    values = dotenv_values(ROOT / '.env.local')
    failed = False
    for name, probe in [('tigris', probe_tigris), ('hf', probe_hf)]:
        key = '_connection-test/' + str(uuid.uuid4()) + '.txt'
        try:
            probe(values, key, b'VeloNexo storage probe\n')
            print(name + ': upload/read/integrity/delete PASS', flush=True)
        except Exception as error:
            failed = True
            response = getattr(error, 'response', {})
            code = response.get('Error', {}).get('Code', '') if isinstance(response, dict) else getattr(response, 'status_code', '')
            # Never print raw exceptions: URLs or credentials may be included.
            print(f'{name}: FAIL {type(error).__name__} {code}; test key: {key}', flush=True)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
