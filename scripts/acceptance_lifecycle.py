"""Exercise actual CLI publication, withdrawal, restore and purge on a synthetic local clip."""
import json
from pathlib import Path
import subprocess
import sys
import media_publish as m


def main():
    remote='--remote' in sys.argv
    baseline=m.read(m.CATALOG);backup=m.STATE/'acceptance-before.json';m.atomic(backup,baseline)
    def run(*args,success=True):
        r=subprocess.run([sys.executable,str(m.ROOT/'scripts/media_publish.py'),*args],capture_output=True,text=True)
        if (r.returncode==0)!=success:raise AssertionError('Unexpected CLI result: '+args[0]+' '+r.stderr)
        return r
    try:
        source=m.ROOT/('.local/fixtures/portrait-audio.mp4' if remote else '.local/acceptance/source-01.mp4')
        run('publish','--input',str(source),'--id','lifecycle-test','--title','Prueba de recuperación',*(() if remote else ('--provider','local')))
        dest,media=m.find_map('lifecycle-test')
        assert (m.STATE/'sources'/(media['source_sha256']+'.source')).exists()
        run('withdraw','lifecycle-test');assert next(v for v in m.read(m.CATALOG)['videos'] if v['id']=='lifecycle-test')['visibility']=='removed'
        assert (dest/'play.m3u8').exists()
        run('restore-entry','lifecycle-test');assert next(v for v in m.read(m.CATALOG)['videos'] if v['id']=='lifecycle-test')['visibility']=='published'
        run('purge','lifecycle-test',success=False)
        run('withdraw','lifecycle-test');run('purge','lifecycle-test')
        assert not (dest/'play.m3u8').exists()
        assert all(not (dest/o['file']).exists() for o in media['objects'])
        if remote:
            from urllib.request import urlopen,Request
            from urllib.error import HTTPError
            adapters=m.stores(m.config())
            for o in media['objects']:
                try:
                    with urlopen(Request(adapters[o['provider_id']].url(o['object_key'],'HEAD'),method='HEAD'),timeout=20) as response:
                        raise AssertionError('Purged object still accessible')
                except HTTPError as error:
                    assert error.code==404, error.code
        run('restore-entry','lifecycle-test',success=False)
        run('restore-catalog',str(backup))
        assert m.read(m.CATALOG)==baseline
        m.atomic(m.STATE/('remote-lifecycle-evidence.json' if remote else 'lifecycle-evidence.json'),{'checked_at':m.now(),'publish':True,'source_backup':True,'withdraw_keeps_source':True,'restore_entry':True,'purge_requires_withdraw':True,'purged_media_not_restorable':True,'catalog_restored':True})
        print('PASS: publish/source backup/withdraw/restore/purge/catalog recovery')
    finally:
        if m.read(m.CATALOG)!=baseline:m.save_catalog(baseline)


if __name__=='__main__':main()
