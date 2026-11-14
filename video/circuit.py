"""Schemdraw circuit with fixed geometry and proportional IEEE symbols."""
import json
from pathlib import Path
import schemdraw
import schemdraw.elements as elm
from schemdraw.segments import SegmentPoly

FG = '#dbe7f3'
RED = '#ff5c6c'
TEAL = '#25d0bb'
BG = '#071729'


def resistor():
    # Reduce both the body length and the zigzag width, preserving lead endpoints.
    return elm.ResistorIEEE().scalex(.75).scaley(.45)


def generate_circuits(assets: Path):
    assets.mkdir(parents=True, exist_ok=True)
    schemdraw.use('svg')
    bounds = []
    for closed, filename in [(False, 'circuit.svg'), (True, 'circuit_closed.svg')]:
        with schemdraw.Drawing(show=False) as drawing:
            drawing.config(unit=2, color=FG, lw=1.8)
            drawing += elm.SourceSin().scale(.82).at((0, 0)).to((0, 3.2))
            drawing += resistor().at((0, 3.2)).to((2.1, 3.2))
            drawing += elm.Inductor().scale(.80).at((2.1, 3.2)).to((4.3, 3.2))
            drawing += elm.Line().at((4.3, 3.2)).to((12, 3.2))
            drawing += elm.Line().at((0, 0)).to((12, 0))
            drawing += elm.SourceI().scale(.82).at((4.3, 0)).to((4.3, 3.2))
            drawing += resistor().at((6.3, 3.2)).to((6.3, 0))
            drawing += elm.Inductor().scale(.80).at((8.1, 3.2)).to((8.1, 0))
            drawing += elm.Capacitor().scale(.80).at((9.9, 3.2)).to((9.9, 0))
            for x in [4.3, 6.3, 8.1, 9.9]:
                drawing += elm.Dot(radius=.045).at((x, 3.2)).color(TEAL if x == 4.3 else FG)
                drawing += elm.Dot(radius=.035).at((x, 0))
            drawing += elm.Ground().scale(.65).at((0, 0))

            # Same contacts in both states; only the physical blade moves.
            drawing += elm.Line().at((12, 3.2)).to((12, 2.85)).color(RED)
            tip = (12, 2.30) if closed else (12.32, 2.40)
            drawing += elm.Line().at((12, 2.85)).to(tip).color(RED)
            drawing += resistor().at((12, 2.30)).to((12, 0)).color(RED)
            for y in [2.85, 2.30]:
                drawing += elm.Dot(radius=.045, open=True).at((12, y)).color(RED).fill(BG)
            # A code-native Schemdraw polygon supplies the fault lightning icon.
            bolt = elm.Element()
            bolt.segments.append(SegmentPoly([
                (12.85, 1.95), (12.48, 1.38), (12.76, 1.38),
                (12.60, .88), (13.10, 1.56), (12.82, 1.56)],
                color=RED, fill=RED, lw=.8))
            drawing += bolt.at((0, 0)).theta(0)
            bbox = drawing.get_bbox()
            bounds.append([bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax])
            drawing.save(assets / filename)
    if bounds[0] != bounds[1]:
        raise ValueError('Switch motion must not change the circuit scale or alignment.')
    metadata = {
        'bounds': bounds[0], 'fault_highlight_center': [12.3, 1.6],
        'labels': {
            'source': [-.85, 1.6], 'r_th': [1.05, 3.68],
            'l_th': [3.2, 3.68], 'pcc': [4.75, 3.68],
            'iq': [3.53, 1.6], 'r_load': [6.90, 1.6],
            'l_load': [8.68, 1.6], 'c_pcc': [10.60, 1.6],
            'r_fault': [11.45, 1.15], 'switch': [11.5, 2.63]},
        'symbols': 'Schemdraw IEEE resistors, coils, capacitors and sources',
        'fault_color': RED, 'fixed_bounds_in_both_states': True}
    (assets / 'circuit_layout.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')


if __name__ == '__main__':
    generate_circuits(Path(__file__).resolve().parent / 'assets')
