"""Generate a synthetic HLS fixture and verify delivery from both real stores."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from storage_probe import ROOT, dotenv_values, boto3, Config, batch_bucket_files


def main():
    values = dotenv_values(ROOT / '.env.local')
    work = ROOT / '.local/hls-smoke'
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi',
        '-i', 'testsrc2=size=360x640:rate=24', '-t', '12', '-c:v', 'libx264',
        '-preset', 'ultrafast', '-crf', '30', '-pix_fmt', 'yuv420p', '-g', '48',
        '-keyint_min', '48', '-sc_threshold', '0', '-an', '-f', 'hls', '-hls_time', '2',
        '-hls_playlist_type', 'vod', '-hls_segment_type', 'fmp4',
        '-hls_segment_filename', 'seg_%03d.m4s', 'index.m3u8'], cwd=work, check=True)
    files = [work / 'init.mp4', *sorted(work.glob('seg_*.m4s'))]
    revision = hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()[:12]
    prefix = f'demo/synthetic/{revision}'
    client = boto3.client('s3', endpoint_url=values['TIGRIS_ENDPOINT_URL'],
        region_name=values['TIGRIS_REGION'], aws_access_key_id=values['TIGRIS_ACCESS_KEY_ID'],
        aws_secret_access_key=values['TIGRIS_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4', connect_timeout=10, read_timeout=20,
                      retries={'total_max_attempts': 2}, s3={'addressing_style':'path'}))
    # Tiny shared init is duplicated. First three segments use Tigris, remaining three HF.
    placements = {p.name: ('tigris' if i < 4 else 'hf') for i,p in enumerate(files)}
    for p in files[:4]:
        client.put_object(Bucket=values['TIGRIS_BUCKET'], Key=f'{prefix}/{p.name}',
                          Body=p.read_bytes(), ContentType='video/mp4')
    batch_bucket_files(values['HF_BUCKET'], add=[(p, f'{prefix}/{p.name}') for p in [files[0],*files[4:]]], token=values['HF_TOKEN'])
    print('Synthetic segments uploaded to both stores', flush=True)
    report, objects, urls = [], [], {}
    for p in files:
        provider = placements[p.name]; key=f'{prefix}/{p.name}'
        if provider == 'tigris':
            # A short-lived signed URL preserves the existing private bucket setting.
            url=client.generate_presigned_url('get_object', Params={'Bucket':values['TIGRIS_BUCKET'],'Key':key},ExpiresIn=3600)
        else:
            url='https://huggingface.co/buckets/'+values['HF_BUCKET']+'/resolve/'+quote(key,safe='')
        urls[p.name]=url
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        objects.append({'file':p.name,'provider_id':provider,'object_key':key,'size_bytes':p.stat().st_size,'sha256':digest})
        try:
            req=Request(url,headers={'Origin':'http://localhost:5173'})
            with urlopen(req,timeout=30) as response:
                data=response.read()
                report.append({'file':p.name,'provider':provider,'status':response.status,
                    'integrity':hashlib.sha256(data).hexdigest()==digest,
                    'cors':response.headers.get('Access-Control-Allow-Origin'),
                    'content_type':response.headers.get('Content-Type')})
        except HTTPError as e:
            report.append({'file':p.name,'provider':provider,'status':e.code})
        except Exception as e:
            report.append({'file':p.name,'provider':provider,'error':type(e).__name__})
    manifest=(work/'index.m3u8').read_text()
    manifest=manifest.replace('URI="init.mp4"','URI="'+urls['init.mp4']+'"')
    manifest='\n'.join(urls.get(line,line) for line in manifest.splitlines())+'\n'
    (work/'remote.m3u8').write_text(manifest)
    (work/'media-map.json').write_text(json.dumps({'video_id':'synthetic','revision':revision,'objects':objects},indent=2))
    (work/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return 0 if all(r.get('integrity') for r in report) else 1


if __name__ == '__main__':
    sys.exit(main())
