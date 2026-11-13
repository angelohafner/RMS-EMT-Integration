"""Six narrated chapters using real measurements, Schemdraw SVG and MathTex."""
import json
from pathlib import Path
import numpy as np
from manim import *

HERE=Path(__file__).resolve().parent
BG='#071729';FG='#EDF4FA';MUTED='#91A8BE';TEAL='#25D0BB';PURPLE='#B18CFF';GOLD='#FFB454';RED='#FF5C6C'
config.background_color=BG


def words(text,size=28,color=FG):
    return Text(text,font='Arial',font_size=size,color=color)


def equation(text,size=36,color=FG):
    return MathTex(text,font_size=size,color=color)


def card(title,subtitle,color,width=2.65,height=1.35):
    box=RoundedRectangle(width=width,height=height,corner_radius=.14,stroke_color=color,stroke_width=2,
        fill_color='#102B41',fill_opacity=1)
    a=words(title,26,color);b=words(subtitle,18,MUTED)
    content=VGroup(a,b).arrange(DOWN,buff=.17)
    if content.width>width-.28:content.scale_to_fit_width(width-.28)
    return VGroup(box,content)


class RMSIntegrationFilm(Scene):
    def construct(self):
        self.timeline=json.loads((HERE/'timeline.json').read_text())
        self.data=np.load(HERE/'assets/measurements.npz')
        self.evidence=json.loads((HERE/'assets/provenance.json').read_text())
        functions=[self.concept,self.resolution,self.transfer,self.fault,self.results,self.limits]
        for index,(chapter,fn) in enumerate(zip(self.timeline['chapters'],functions),start=1):
            self.start_time=self.time
            self.chapter=chapter
            self.add_sound(str(HERE/chapter['audio_file']),time_offset=chapter['audio_offset_s'])
            heading=words(chapter['title'],34).to_edge(UP,buff=.34)
            chapter_tag=words(f'RMS–EMT  /  {index:02d}',16,MUTED).to_corner(DR,buff=.22)
            line=Line([-6.55,2.97,0],[6.55,2.97,0],stroke_color='#254258',stroke_width=1)
            self.add(heading,chapter_tag,line)
            fn()
            remaining=chapter['duration_s']-(self.time-self.start_time)-.4
            if remaining<0:raise RuntimeError(f'Chapter {index} animation exceeds its narration schedule.')
            self.wait(remaining)
            self.play(FadeOut(Group(*self.mobjects)),run_time=.4)
        if abs(self.time-self.timeline['duration_s'])>.12:raise RuntimeError('Animation timing drift.')

    def at(self,seconds):
        remaining=seconds-(self.time-self.start_time)
        if remaining>0:self.wait(remaining)

    def concept(self):
        subtitle=words('A verified weak-grid STATCOM demonstration',26,MUTED).move_to([0,2.37,0])
        specs=VGroup(equation(r'230\ \mathrm{kV}',44,TEAL),equation(r'\pm100\ \mathrm{MVAr}',44,GOLD),
                     equation(r'\mathrm{SCR}\approx3',40,PURPLE)).arrange(RIGHT,buff=1.15).move_to([0,1.5,0])
        self.play(FadeIn(subtitle),LaggedStart(*[FadeIn(x,shift=UP*.2) for x in specs],lag_ratio=.2),run_time=1.4)
        labels=[('PSS/E','Power flow + boundary',PURPLE),('Python','Units + parameters',GOLD),('PSCAD','EMT waveforms',TEAL),('Compare','RMS + EMT evidence',FG)]
        boxes=VGroup(*[card(*x) for x in labels]).arrange(RIGHT,buff=.62).move_to([0,-.25,0])
        arrows=VGroup(*[Arrow(boxes[i].get_right(),boxes[i+1].get_left(),buff=.08,color=MUTED,stroke_width=3,max_tip_length_to_length_ratio=.2) for i in range(3)])
        self.at(5)
        for i,box in enumerate(boxes):
            self.play(FadeIn(box,shift=RIGHT*.15),run_time=.45)
            if i<3:self.play(GrowArrow(arrows[i]),run_time=.3)
        self.play(FadeIn(words('Solve → transfer → simulate → compare',26).move_to([0,-1.65,0])),run_time=.6)
        self.at(13)
        self.play(FadeIn(words('Sequential and offline',24,GOLD).move_to([0,-2.5,0])),run_time=.6)

    def resolution(self):
        left=card('RMS dynamics','Fundamental-frequency phasors',PURPLE,width=5.7,height=4.1).move_to([-3.35,.3,0])
        right=card('EMT','Instantaneous phase waveforms',TEAL,width=5.7,height=4.1).move_to([3.35,.3,0])
        left[1].move_to([-3.35,1.85,0]);right[1].move_to([3.35,1.85,0])
        self.play(FadeIn(left),FadeIn(right),run_time=.7)
        origin=np.array([-3.35,-.25,0]);radius=1.15
        circle=Circle(radius=radius,color='#34516A',stroke_width=1).move_to(origin)
        axis=VGroup(Line(origin+LEFT*1.45,origin+RIGHT*1.45,color=MUTED,stroke_width=1),Line(origin+DOWN*1.4,origin+UP*1.4,color=MUTED,stroke_width=1))
        theta=ValueTracker(.35)
        arrow=always_redraw(lambda:Arrow(origin,origin+radius*np.array([np.cos(theta.get_value()),np.sin(theta.get_value()),0]),buff=0,color=PURPLE,stroke_width=5))
        phasor=equation(r'\underline V=V_{\mathrm{ph}}e^{j\theta}',30,PURPLE).move_to([-3.35,-1.4,0])
        ax=Axes(x_range=[0,2*PI,PI],y_range=[-1.3,1.3,1],x_length=4.5,y_length=2.1,tips=False,
            axis_config={'color':MUTED,'include_ticks':False}).move_to([3.35,-.25,0])
        wave=always_redraw(lambda:ax.plot(lambda x:np.cos(x+theta.get_value()),x_range=[0,2*PI,.08],color=TEAL,stroke_width=3))
        self.play(Create(circle),Create(axis),Create(ax),GrowArrow(arrow),Create(wave),Write(phasor),run_time=1.1)
        self.play(theta.animate.set_value(.35+2*PI),run_time=4,rate_func=linear)
        arrow.clear_updaters();wave.clear_updaters()
        self.at(9)
        expression=equation(r'v_a(t)=\sqrt{2}\,V_{\mathrm{ph}}\cos(2\pi ft+\theta)',35).move_to([0,-2.5,0])
        self.play(Write(expression),run_time=1.2)
        self.play(FadeIn(words('Concept illustration • comparisons use matched measurement windows',19,MUTED).move_to([0,-3.15,0])),run_time=.5)

    def transfer(self):
        op=self.evidence['op']['capacitive']
        box=RoundedRectangle(width=5.8,height=4.7,corner_radius=.16,fill_color='#102B41',fill_opacity=1,stroke_color=PURPLE).move_to([-3.4,.05,0])
        title=words('Solved boundary at the PCC',26,PURPLE).move_to([-3.4,1.95,0])
        values=VGroup(equation(rf'V_{{\mathrm{{PCC}}}}={op["pcc_voltage_pu"]:.4f}\ \mathrm{{pu}}',34),
            equation(r'P_{\mathrm{load}}=30\ \mathrm{MW}',33),equation(r'Q_{\mathrm{load}}=10\ \mathrm{MVAr}',33),
            equation(r'Q_{\mathrm{STATCOM},0}=+20\ \mathrm{MVAr}',33)).arrange(DOWN,buff=.35).move_to([-3.4,-.05,0])
        self.play(FadeIn(box),FadeIn(title),LaggedStart(*[Write(x) for x in values],lag_ratio=.18),run_time=2)
        rhs=VGroup(equation(r'Z_{\mathrm{Th}}=R+jX',40,TEAL),
            equation(r'R=\operatorname{Re}(Z_{\mathrm{Th}})',38),
            equation(r'L=\frac{\operatorname{Im}(Z_{\mathrm{Th}})}{2\pi f}',38),
            equation(rf'R={op["r_ohm"]:.2f}\ \Omega,\quad L={op["l_h"]:.4f}\ \mathrm{{H}}',31,GOLD)).arrange(DOWN,buff=.42).move_to([3.25,.2,0])
        self.at(4);self.play(Write(rhs[0]),run_time=.7)
        self.at(8);self.play(Write(rhs[1]),run_time=.7)
        self.at(11);self.play(Write(rhs[2]),run_time=1)
        self.at(14);self.play(Write(rhs[3]),run_time=.7)
        self.play(FadeIn(words('Per-phase impedance in ohms • explicit three-phase bases and signs',20,MUTED).move_to([0,-2.85,0])),run_time=.5)

    def fault(self):
        svg=SVGMobject(str(HERE/'assets/circuit.svg')).set(width=12.25).move_to([0,.65,0])
        self.play(Create(svg),run_time=1.6)
        # Labels are LaTeX objects; Schemdraw supplies the circuit symbols.
        labels=VGroup(equation(r'E_{\mathrm{Th}}',28).move_to([-6.55,.65,0]),
            equation(r'R_{\mathrm{Th}}',28).move_to([-4.3,2.58,0]),
            equation(r'L_{\mathrm{Th}}',28).move_to([-1.7,2.58,0]),
            equation(r'V_{\mathrm{PCC}}',28,TEAL).move_to([-.6,2.58,0]),
            equation(r'I_q',29,TEAL).move_to([-1.55,.65,0]),
            equation(r'R_{\ell}',26).move_to([1.8,.7,0]),
            equation(r'L_{\ell}',26).move_to([3.25,.7,0]),
            equation(r'C_{\mathrm{PCC}}',26).move_to([4.65,.7,0]),
            equation(r'R_f',28,RED).move_to([6.2,.3,0]))
        self.play(LaggedStart(*[FadeIn(x) for x in labels],lag_ratio=.06),run_time=.9)
        self.play(FadeIn(words('Balanced three-phase system • one-phase equivalent shown',20,MUTED).move_to([0,-1.25,0])),run_time=.5)
        limit=equation(r'I_{\max}=\frac{100\ \mathrm{MVAr}}{\sqrt{3}\,(230\ \mathrm{kV})}=0.251\ \mathrm{kA}',34,GOLD).move_to([0,-2,0])
        self.at(4);self.play(Write(limit),run_time=1)
        time_line=NumberLine(x_range=[.8,1.4,.1],length=10,include_numbers=True,font_size=22,decimal_number_config={'num_decimal_places':2},color=MUTED).move_to([0,-2.9,0])
        fault_band=Line(time_line.n2p(1),time_line.n2p(1.15),color=RED,stroke_width=10)
        duration=equation(r'\Delta t_f=150\ \mathrm{ms}',29,RED).move_to([3.8,-2.18,0])
        # Move the limit upward slightly to leave an uncluttered event timeline.
        self.at(8);self.play(FadeOut(limit),Create(time_line),run_time=.5)
        self.play(Create(fault_band),Write(duration),run_time=.6)
        moving=Dot(time_line.n2p(.8),color=GOLD,radius=.07)
        self.add(moving);self.play(moving.animate.move_to(time_line.n2p(1)),run_time=1.2,rate_func=linear)
        highlight=RoundedRectangle(width=1.05,height=2.7,corner_radius=.1,color=RED,fill_color=RED,fill_opacity=.15).move_to([5.57,.65,0])
        closed=SVGMobject(str(HERE/'assets/circuit_closed.svg')).set(width=12.25).move_to([0,.65,0])
        self.play(Transform(svg,closed),FadeIn(highlight),run_time=.2)
        self.play(moving.animate.move_to(time_line.n2p(1.15)),run_time=1.5,rate_func=linear)
        opened=SVGMobject(str(HERE/'assets/circuit.svg')).set(width=12.25).move_to([0,.65,0])
        self.play(Transform(svg,opened),FadeOut(highlight),run_time=.2)
        self.play(moving.animate.move_to(time_line.n2p(1.4)),run_time=1,rate_func=linear)

    def plot_row(self,key,range_y,ypos,label):
        ax=Axes(x_range=[.8,1.4,.1],y_range=range_y,x_length=10.7,y_length=1.15,tips=False,
            axis_config={'color':'#526C82','stroke_width':1,'font_size':20},
            x_axis_config={'include_numbers':key=='q_mvar','numbers_to_include':[.8,1,1.15,1.4],'decimal_number_config':{'num_decimal_places':2}},
            y_axis_config={'include_numbers':True}).move_to([.6,ypos,0])
        variable,unit=label.split(r'\ ')
        lab=VGroup(equation(variable,27),equation(unit,23)).arrange(DOWN,buff=.08).move_to([-5.95,ypos,0])
        curves=[]
        for engine,color in [('emt',TEAL),('rms',PURPLE)]:
            name=f'capacitive_{engine}_{key}';t=self.data[name+'_t'];value=self.data[name]
            line=VMobject(color=color,stroke_width=2.7).set_points_as_corners([ax.c2p(a,b) for a,b in zip(t,value)])
            curves.append(line)
        band=Polygon(ax.c2p(1,range_y[0]),ax.c2p(1.15,range_y[0]),ax.c2p(1.15,range_y[1]),ax.c2p(1,range_y[1]),
            stroke_width=0,fill_color=RED,fill_opacity=.1)
        return ax,lab,band,curves

    def results(self):
        legend=VGroup(words('PSCAD EMT',21,TEAL),words('PSS/E RMS',21,PURPLE),words('One-cycle windows • initial capacitive case',20,MUTED)).arrange(RIGHT,buff=.55).move_to([0,2.52,0])
        self.add(legend)
        rows=[self.plot_row('v_pu',[0,1.6,.5],1.48,r'V_{\mathrm{PCC}}\ (\mathrm{pu})'),
              self.plot_row('i_ka',[0,.3,.1],-.12,r'I_{\mathrm{STATCOM}}\ (\mathrm{kA})'),
              self.plot_row('q_mvar',[0,140,50],-1.72,r'Q_{\mathrm{STATCOM}}\ (\mathrm{MVAr})')]
        for ax,lab,band,curves in rows:self.add(band,ax,lab)
        self.play(LaggedStart(*[Create(curve) for row in rows for curve in row[3]],lag_ratio=.12),run_time=4)
        self.add(equation(r't\ (\mathrm{s})',25).move_to([5.9,-2.68,0]))
        self.at(7)
        note=words('Current and reactive power track closely after window alignment.',21).move_to([0,-3.22,0])
        self.play(FadeIn(note),run_time=.5)
        self.at(11)
        pointer=Arrow([2.7,2.4,0],rows[0][0].c2p(1.166,1.5),color=GOLD,buff=.06,stroke_width=3)
        self.play(GrowArrow(pointer),run_time=.5)
        self.play(Transform(note,words('Clearing voltage differs: network energy and angle tracking matter.',21,GOLD).move_to([0,-3.22,0])),run_time=.6)

    def limits(self):
        checks=VGroup(card('Physical checks','Native RMS + native EMT',TEAL,3.6,1.3),
            card('Step refinement','Passed in both domains',TEAL,3.6,1.3),
            card('Reproducible','Python + native artifacts',TEAL,3.6,1.3)).arrange(RIGHT,buff=.45).move_to([0,1.65,0])
        self.play(LaggedStart(*[FadeIn(x,shift=UP*.2) for x in checks],lag_ratio=.15),run_time=1.3)
        limitations=VGroup(words('Matched terminal controls; different transient models.',27),
            words('No PWM, DC-link energy limits or manufacturer protection.',25,MUTED),
            words('Scalar RMS filtering versus EMT vector / angle tracking.',25,MUTED)).arrange(DOWN,buff=.35).move_to([0,-.1,0])
        self.at(4);self.play(LaggedStart(*[FadeIn(x) for x in limitations],lag_ratio=.3),run_time=1.3)
        self.at(10)
        takeaway=words('Sequential integration — no real-time solver exchange',29,GOLD).move_to([0,-1.8,0])
        self.play(FadeIn(takeaway),run_time=.7)
        self.at(14)
        self.play(FadeIn(words('Transfer the boundary. Run independently. Compare the evidence.',24,TEAL).move_to([0,-2.65,0])),run_time=.7)
        self.add(words('AI-generated English narration • real licensed simulation results',16,MUTED).move_to([0,-3.3,0]))
