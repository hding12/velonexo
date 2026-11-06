"""Small storage adapters. Secrets stay in .env.local; no media proxy."""
import hashlib
import mimetypes
from urllib.parse import quote
from urllib.request import Request, urlopen
from storage_probe import ROOT, ENV_FILE, boto3, Config, batch_bucket_files, dotenv_values


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def content_type(name):
    return {'.m4s': 'video/iso.segment', '.mp4': 'video/mp4', '.webp': 'image/webp'}.get(
        __import__('pathlib').Path(name).suffix, mimetypes.guess_type(name)[0] or 'application/octet-stream')


class Store:
    def __init__(self, config, values):
        self.config = config
        self.id = config['id']
        self.kind = config['type']
        self.bucket = values[config['bucket_env']]
        if self.kind == 's3':
            self.client = boto3.client('s3', endpoint_url=values[config['endpoint_env']],
                region_name=values[config['region_env']],
                aws_access_key_id=values[config['access_key_env']],
                aws_secret_access_key=values[config['secret_key_env']],
                config=Config(signature_version='s3v4', connect_timeout=10, read_timeout=20,
                    retries={'total_max_attempts': 2}, s3={'addressing_style': 'path'}))
        elif self.kind == 'hf':
            self.token = values[config['token_env']]
        else:
            raise ValueError('Unsupported provider type')

    def identity(self):
        return {'type': self.kind, 'bucket': self.bucket,
            'endpoint': self.client.meta.endpoint_url if self.kind == 's3' else 'https://huggingface.co'}

    def upload(self, path, key):
        if self.kind == 's3':
            self.client.upload_file(str(path), self.bucket, key, ExtraArgs={'ContentType': content_type(path.name)})
        else:
            batch_bucket_files(self.bucket, add=[(path, key)], token=self.token)

    def url(self, key, method='GET'):
        if self.kind == 's3':
            return self.client.generate_presigned_url('head_object' if method == 'HEAD' else 'get_object',
                Params={'Bucket': self.bucket, 'Key': key}, ExpiresIn=3600)
        return 'https://huggingface.co/buckets/' + self.bucket + '/resolve/' + quote(key, safe='')

    def delete(self, key):
        try:
            if self.kind == 's3':
                self.client.delete_object(Bucket=self.bucket, Key=key)
            else:
                batch_bucket_files(self.bucket, delete=[key], token=self.token)
        except Exception as error:
            response = getattr(error, 'response', None)
            status = response.get('ResponseMetadata', {}).get('HTTPStatusCode') if isinstance(response, dict) else getattr(response, 'status_code', None)
            if status != 404:
                raise

    def verify(self, obj):
        headers = {'Origin': 'http://127.0.0.1:5174'}
        with urlopen(Request(self.url(obj['object_key']), headers=headers), timeout=25) as r:
            h = hashlib.sha256()
            size = 0
            for chunk in iter(lambda: r.read(1024 * 1024), b''):
                size += len(chunk)
                h.update(chunk)
            if h.hexdigest() != obj['sha256'] or size != obj['size_bytes']:
                raise ValueError('Remote integrity mismatch')
            cors = r.headers.get('Access-Control-Allow-Origin')
            if cors not in ('*', headers['Origin']):
                raise ValueError('Remote CORS unavailable')
            mime = r.headers.get_content_type()
            if obj['file'].endswith(('.m4s', '.mp4')) and mime not in ('video/mp4', 'video/iso.segment', 'application/octet-stream'):
                raise ValueError('Remote media MIME mismatch')
        with urlopen(Request(self.url(obj['object_key'], 'HEAD'), method='HEAD', headers=headers), timeout=25) as r:
            if int(r.headers.get('Content-Length', -1)) != obj['size_bytes']:
                raise ValueError('Remote HEAD length mismatch')
        with urlopen(Request(self.url(obj['object_key']), headers={**headers, 'Range': 'bytes=0-15'}), timeout=25) as r:
            if r.status != 206 or len(r.read(17)) != min(16, obj['size_bytes']):
                raise ValueError('Remote Range unsupported')
        return {'get_sha256': True, 'head': True, 'range': True, 'cors': cors, 'mime': mime}


def stores(config):
    values = dotenv_values(ENV_FILE)
    return {p['id']: Store(p, values) for p in config['providers']}
