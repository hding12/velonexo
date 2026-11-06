"""Generate distinct, non-explicit local clips for 30/50-card acceptance."""
import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
import media_publish as m


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=50);args=parser.parse_args()
    if not 1<=args.count<=50:raise ValueError('count must be 1..50')
    work=m.RUNTIME/'acceptance';work.mkdir(parents=True,exist_ok=True)
    entries=[]
    for i in range(args.count):
        source=work/f'source-{i:02}.mp4'
        width,height=[(160,284),(284,160),(192,192)][i%3]
        audio=i%4==0
        if not source.exists():
            cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'testsrc2=size={width}x{height}:rate=24']
            if audio:cmd+=['-f','lavfi','-i',f'sine=frequency={220+i*10}:sample_rate=48000']
            cmd+=['-t',str(2.5+i%4),'-vf',f'hue=h={i*7}','-c:v','libx264','-preset','ultrafast','-crf','32']
            if audio:cmd+=['-c:a','aac','-shortest']
            m.command(cmd+[str(source)])
        video_id=f'acceptance-{i:02}'
        dest,media=m.prepare(source,video_id,m.config(),'local');m.refresh(dest,media,{})
        base=f'/local-media/{video_id}/{media["revision"]}'
        entries.append({'id':video_id,'title':f'Video de prueba {i+1}','creator':'@velonexo','visibility':'published',
            'source':{'kind':'native','format':'hls','playlist':base+'/play.m3u8','media_map':base+'/map.json'},
            'poster':base+'/poster.jpg','category':['vertical','horizontal','cuadrado'][i%3],
            'has_audio':audio,'tags':['prueba','sonido' if audio else 'silencio'],
            'published_at':(datetime(2026,11,6,tzinfo=timezone.utc)-timedelta(minutes=i)).isoformat()})
        print(f'Prepared {i+1}/{args.count}',flush=True)
    m.atomic(work/'catalog.json',{'schema_version':1,'videos':entries})
    print('Acceptance catalog ready; default catalog unchanged')


if __name__=='__main__':main()
