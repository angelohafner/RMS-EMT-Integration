"""Render individual corrected chapters with the production layout and narration."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scenes import *


class ChapterPreview(RMSIntegrationFilm):
    chapter_index = 1
    method = 'resolution'

    def construct(self):
        self.timeline = json.loads((HERE / 'timeline.json').read_text(encoding='utf8'))
        self.data = np.load(HERE / 'assets/measurements.npz')
        self.evidence = json.loads((HERE / 'assets/provenance.json').read_text(encoding='utf8'))
        self.chapter = self.timeline['chapters'][self.chapter_index]
        self.start_time = self.time
        self.add_sound(str(HERE / self.chapter['audio_file']), time_offset=self.chapter['audio_offset_s'])
        self.add(words(self.chapter['title'], 34).to_edge(UP, buff=.34),
                 words(f'RMS–EMT  /  {self.chapter_index+1:02d}', 16, MUTED).to_corner(DR, buff=.22),
                 Line([-6.55, 2.97, 0], [6.55, 2.97, 0], stroke_color='#254258', stroke_width=1))
        getattr(self, self.method)()
        remaining = self.chapter['duration_s'] - (self.time - self.start_time) - .4
        if remaining < 0:
            raise RuntimeError('Chapter exceeds its original narration timing.')
        self.wait(remaining)
        self.play(FadeOut(Group(*self.mobjects)), run_time=.4)


class PhasorPreview(ChapterPreview):
    pass


class CircuitPreview(ChapterPreview):
    chapter_index = 3
    method = 'fault'


class ResultsPreview(ChapterPreview):
    chapter_index = 4
    method = 'results'
