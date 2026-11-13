"""Mux English subtitles, audit technical output and create review frames."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent


def call(args):
    p=subprocess.run(args,capture_output=True,text=True,encoding='utf8',errors='replace')
    if p.returncode:raise RuntimeError(p.stderr[-3000:])
    return p.stdout,p.stderr


def main():
    source=HERE/'media/videos/scenes/1080p30/RMSIntegrationFilm.mp4'
    out=HERE/'output';out.mkdir(exist_ok=True)
    final=out/'RMS_EMT_Integration_EN_1080p.mp4'
    call(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),'-i',str(HERE/'narration_en.srt'),
        '-map','0:v:0','-map','0:a:0','-map','1:0','-c:v','copy','-c:a','copy','-c:s','mov_text',
        '-metadata:s:a:0','language=eng','-metadata:s:s:0','language=eng','-disposition:s:0','0',
        '-metadata','title=Sequential RMS–EMT Integration | PSS/E and PSCAD',
        '-metadata','comment=AI-generated English narration; actual licensed simulation data; averaged terminal models.',
        '-movflags','+faststart',str(final)])
    info=json.loads(call(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(final)])[0])
    video=next(x for x in info['streams'] if x['codec_type']=='video')
    audio=next(x for x in info['streams'] if x['codec_type']=='audio')
    length=float(info['format']['duration']);timeline=json.loads((HERE/'timeline.json').read_text())
    if video['width']!=1920 or video['height']!=1080 or video['r_frame_rate']!='30/1':raise ValueError('Incorrect video format.')
    if not 90<=length<=120 or abs(length-timeline['duration_s'])>.15:raise ValueError('Incorrect movie duration/timing.')
    _,decode=call(['ffmpeg','-v','error','-i',str(final),'-f','null','-'])
    if decode.strip():raise ValueError('Decode emitted errors: '+decode)
    _,level=call(['ffmpeg','-hide_banner','-i',str(final),'-vn','-af','volumedetect','-f','null','-'])
    (out/'audio_levels.txt').write_text(level,encoding='utf8')
    mean=float(re.search(r'mean_volume:\s*([-\d.]+)',level).group(1));peak=float(re.search(r'max_volume:\s*([-\d.]+)',level).group(1))
    if mean< -35 or peak>-.05:raise ValueError(f'Audio is silent/too quiet or clipped: mean={mean}, peak={peak}')
    last=timeline['chapters'][-1]
    if last['start_s']+last['audio_offset_s']+last['audio_duration_s']>length:raise ValueError('Narration is truncated.')
    provenance=json.loads((HERE/'assets/provenance.json').read_text())
    if hashlib.sha256((HERE/'assets/measurements.npz').read_bytes()).hexdigest()!=provenance['dataset_sha256']:raise ValueError('Display dataset changed.')
    source_manifest=json.loads((HERE.parent/'delivery/RMS_EMT_STATCOM_Dynamic_v2_MANIFEST.json').read_text())['files']
    for curve in provenance['curves'].values():
        if curve['source_sha256']!=source_manifest[curve['source_file']]:raise ValueError('Display data differs from validated release.')
        if curve['reduced_min']!=curve['full_interval_min'] or curve['reduced_max']!=curve['full_interval_max']:raise ValueError('Plot lost extrema.')
    code=(HERE/'scenes.py').read_text()
    if re.search(r'\\(?:Re|Im)(?![A-Za-z])',code):raise ValueError('Stylized real/imaginary operator found.')
    for term in [r'\operatorname{Re}',r'\operatorname{Im}','MathTex','circuit_closed.svg']:
        if term not in code:raise ValueError('Missing requested visual feature: '+term)
    frames=out/'frames';frames.mkdir(exist_ok=True)
    moments=[5,27,50,61,68,81,90,104,112]
    for index,seconds in enumerate(moments):
        call(['ffmpeg','-v','error','-y','-ss',str(seconds),'-i',str(final),'-frames:v','1',str(frames/f'{index+1:02d}_{seconds}s.png')])
    # An FFmpeg contact sheet avoids changing the original render frames.
    select='+'.join(f'eq(n,{round(t*30)})' for t in moments)
    call(['ffmpeg','-v','error','-y','-i',str(final),'-vf',f"select='{select}',scale=640:360,tile=3x3",'-frames:v','1',str(out/'contact_sheet.png')])
    call(['ffmpeg','-v','error','-y','-ss','85','-i',str(final),'-frames:v','1',str(out/'poster.png')])
    result={'passed':True,'duration_s':length,'resolution':[1920,1080],'fps':30,'audio_codec':audio['codec_name'],
        'voice':timeline['voice'],'narration':'AI-generated English, passionate voice profile',
        'mean_volume_db':mean,'max_volume_db':peak,'data_provenance_verified':True,'extrema_preserved':True,
        'decode_errors':0,'subtitles':'English word-timed SRT and optional MP4 subtitle track',
        'video_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'subjective_listening':'Not certified by automated checks; original speech and review preview are supplied.'}
    (out/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
