"""Generate English narration and word-aligned subtitles before rendering."""
import asyncio
import hashlib
import json
import math
from pathlib import Path
import subprocess
import edge_tts

HERE=Path(__file__).resolve().parent


def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration',
        '-of','default=nw=1:nk=1',str(path)],text=True).strip())


def stamp(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


async def main():
    script=json.loads((HERE/'script.json').read_text(encoding='utf8'))
    folder=HERE/'audio';folder.mkdir(exist_ok=True)
    timeline=[];subtitles=[];start=0.
    for chapter in script['chapters']:
        path=folder/(chapter['id']+'.mp3');wordfile=path.with_suffix('.words.json')
        signature=hashlib.sha256(json.dumps([chapter,script['voice'],script['rate'],script['pitch']]).encode()).hexdigest()
        cached=json.loads(wordfile.read_text()) if wordfile.exists() else {}
        if not path.exists() or cached.get('signature')!=signature:
            words=[]
            speech=edge_tts.Communicate(chapter['text'],script['voice'],rate=script['rate'],pitch=script['pitch'],boundary='WordBoundary')
            with path.open('wb') as out:
                async for chunk in speech.stream():
                    if chunk['type']=='audio':out.write(chunk['data'])
                    elif chunk['type']=='WordBoundary':
                        words.append({'start':chunk['offset']/1e7,'end':(chunk['offset']+chunk['duration'])/1e7,'text':chunk['text']})
            wordfile.write_text(json.dumps({'signature':signature,'words':words},indent=2),encoding='utf8')
        else: words=cached['words']
        if not words or path.stat().st_size<3000: raise RuntimeError('TTS returned missing audio or timing.')
        audio_duration=duration(path);scene_duration=math.ceil((audio_duration+1.2)*30)/30
        timeline.append({**chapter,'start_s':start,'duration_s':scene_duration,'audio_duration_s':audio_duration,'audio_offset_s':.5,
            'audio_file':str(path.relative_to(HERE)).replace('\\','/'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        group=[]
        for i,word in enumerate(words):
            group.append(word)
            text=' '.join(w['text'] for w in group)
            if len(text)>=62 or word['text'].endswith(('.','!','?')) or i==len(words)-1:
                subtitles.append((start+.5+group[0]['start'],min(start+.5+group[-1]['end']+.08,start+scene_duration),text))
                group=[]
        print(chapter['id'],round(audio_duration,3),'audio seconds;',scene_duration,'scene seconds',flush=True)
        start+=scene_duration
    if not 90<=start<=120:raise ValueError(f'Narration/scene duration {start:.2f} s is outside 90–120 s. Adjust script/rate explicitly.')
    (HERE/'timeline.json').write_text(json.dumps({'voice':script['voice'],'rate':script['rate'],'pitch':script['pitch'],
        'duration_s':start,'chapters':timeline},indent=2),encoding='utf8')
    srt='\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{text}' for i,(a,b,text) in enumerate(subtitles))+'\n'
    (HERE/'narration_en.srt').write_text(srt,encoding='utf8')
    print('Narration and subtitles ready:',round(start,3),'seconds',flush=True)


if __name__=='__main__':asyncio.run(main())
