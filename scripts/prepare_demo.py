"""Rebuild the three local demo entries; optionally publish a tiny two-store probe."""
import argparse
from datetime import datetime, timezone
import subprocess
import sys
import media_publish as m


def main():
    p=argparse.ArgumentParser();p.add_argument('--remote',action='store_true');args=p.parse_args()
    subprocess.run([sys.executable,str(m.ROOT/'scripts/generate_acceptance.py'),'--count','50'],check=True)
    titles=['Hola, bienvenidos. Un espacio para compartir con buena onda.','Sigue mirando. Este es un video de prueba.','Gracias por pasar por acá.']
    if not m.CATALOG.exists():
        m.atomic(m.CATALOG,m.read(m.ROOT/'config/catalog.example.json'))
    old=m.read(m.CATALOG)
    for i,title in enumerate(titles):
        video_id=f'demo-{i+1}'
        m.publish(argparse.Namespace(input=str(m.ROOT/f'.local/acceptance/source-{i:02}.mp4'),id=video_id,title=title,creator='@velonexo',category=['vertical','horizontal','cuadrado'][i],tag=['prueba','demo']+(['comunidad'] if i==1 else []),provider='local',dry_run=False))
    if args.remote:
        work=m.ROOT/'.local/fixtures';work.mkdir(parents=True,exist_ok=True);source=work/'portrait-audio.mp4'
        if not source.exists():
            m.command(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=360x640:rate=24','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','8','-c:v','libx264','-preset','ultrafast','-crf','30','-c:a','aac','-shortest',str(source)])
        m.publish(argparse.Namespace(input=str(source),id='native-audio',title='Video de prueba con sonido',creator='@velonexo',category='prueba',tag=['prueba','sonido'],provider=None,dry_run=False))
    elif any(v['id']=='native-audio' for v in old['videos']):
        # Do not leave a fresh clone's catalog pointing at an unavailable remote package.
        c=m.read(m.CATALOG)
        for v in c['videos']:
            if v['id']=='native-audio' and not (m.MEDIA/'native-audio').exists():v['visibility']='draft'
        m.save_catalog(c)
    print('Local demo ready. HF public URLs do not require periodic signing.')


if __name__=='__main__':main()
