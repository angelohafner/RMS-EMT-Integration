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
    def play(self,*animations,**kwargs):
        # Cache bookkeeping and encoded clips must use the same whole-frame duration.
        if 'run_time' in kwargs:
            kwargs['run_time']=round(kwargs['run_time']*config.frame_rate)/config.frame_rate
        return super().play(*animations,**kwargs)

    def construct(self):
        self.timeline=json.loads((HERE/'timeline.json').read_text(encoding='utf8'))
        self.data=np.load(HERE/'assets/measurements.npz')
        self.evidence=json.loads((HERE/'assets/provenance.json').read_text(encoding='utf8'))
        timing=[]
        functions=[self.concept,self.resolution,self.transfer,self.fault,self.results,self.limits]
        for index,(chapter,fn) in enumerate(zip(self.timeline['chapters'],functions),start=1):
            # Anchor to the absolute recorded schedule, avoiding cumulative frame rounding.
            self.start_time=chapter['start_s']
            self.chapter=chapter
            # finalize.py assembles all six audio clips independently of Manim caching.
            heading=words(chapter['title'],34).to_edge(UP,buff=.34)
            chapter_tag=words(f'RMS–EMT  /  {index:02d}',16,MUTED).to_corner(DR,buff=.22)
            line=Line([-6.55,2.97,0],[6.55,2.97,0],stroke_color='#254258',stroke_width=1)
            self.add(heading,chapter_tag,line)
            fn()
            remaining=self.start_time+chapter['duration_s']-.4-self.time
            if remaining< -1/config.frame_rate:raise RuntimeError(f'Chapter {index} animation exceeds its narration schedule.')
            self.at(chapter['duration_s']-.4)
            self.play(FadeOut(Group(*self.mobjects)),run_time=.4)
            timing.append({'chapter':index,'requested_end_s':self.start_time+chapter['duration_s'],'rendered_end_s':self.time})
        (HERE/'output').mkdir(exist_ok=True)
        (HERE/'output/render_timing.json').write_text(json.dumps(timing,indent=2),encoding='utf8')
        if abs(self.time-self.timeline['duration_s'])>.12:raise RuntimeError(f'Animation timing drift: {self.time} vs {self.timeline["duration_s"]}.')

    def at(self,seconds):
        target_frame=round((self.start_time+seconds)*config.frame_rate)
        frames=target_frame-round(self.time*config.frame_rate)
        # Cairo floors static wait durations; the tolerance preserves the intended count.
        if frames>0:self.wait((frames+1e-5)/config.frame_rate,frozen_frame=True)

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
        origin=np.array([-3.35,.15,0]);radius=1.0
        circle=Circle(radius=radius,color='#34516A',stroke_width=1).move_to(origin)
        axis=VGroup(Line(origin+LEFT*1.3,origin+RIGHT*1.3,color=MUTED,stroke_width=1),Line(origin+DOWN*1.15,origin+UP*1.15,color=MUTED,stroke_width=1))
        theta=ValueTracker(.35)
        arrow=always_redraw(lambda:Arrow(origin,origin+radius*np.array([np.cos(theta.get_value()),np.sin(theta.get_value()),0]),buff=0,color=PURPLE,stroke_width=5))
        # A separate equation band stays below the complete axis bounding box.
        phasor=equation(r'\underline V=V_{\mathrm{ph}}e^{j\theta}',30,PURPLE).move_to([-3.35,-1.45,0])
        ax=Axes(x_range=[0,2*PI,PI],y_range=[-1.3,1.3,1],x_length=4.5,y_length=2.1,tips=False,
            axis_config={'color':MUTED,'include_ticks':False}).move_to([3.35,.15,0])
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
        svg=SVGMobject(str(HERE/'assets/circuit.svg')).set(width=12.0).move_to([0,.65,0])
        layout=json.loads((HERE/'assets/circuit_layout.json').read_text(encoding='utf8'))
        xmin,ymin,xmax,ymax=layout['bounds']
        def position(point):
            x,y=point
            return np.array([svg.get_left()[0]+(x-xmin)/(xmax-xmin)*svg.width,
                             svg.get_bottom()[1]+(y-ymin)/(ymax-ymin)*svg.height,0])
        self.play(Create(svg),run_time=1.6)
        # Labels are LaTeX objects; Schemdraw supplies the circuit symbols.
        specs=[('source',r'E_{\mathrm{Th}}',FG),('r_th',r'R_{\mathrm{Th}}',FG),
            ('l_th',r'L_{\mathrm{Th}}',FG),('pcc',r'V_{\mathrm{PCC}}',TEAL),
            ('iq',r'I_q',TEAL),('r_load',r'R_{\ell}',FG),('l_load',r'L_{\ell}',FG),
            ('c_pcc',r'C_{\mathrm{PCC}}',FG),('r_fault',r'R_f',RED),('switch',r'S_f',RED)]
        labels=VGroup(*[equation(tex,26,color).move_to(position(layout['labels'][name])) for name,tex,color in specs])
        self.play(LaggedStart(*[FadeIn(x) for x in labels],lag_ratio=.06),run_time=.9)
        self.play(FadeIn(words('Balanced three-phase system • one-phase equivalent shown',20,MUTED).move_to([0,-1.4,0])),run_time=.5)
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
        highlight=RoundedRectangle(width=2.1,height=3.0,corner_radius=.12,color=RED,fill_color=RED,fill_opacity=.08).move_to(position(layout['fault_highlight_center']))
        closed=SVGMobject(str(HERE/'assets/circuit_closed.svg')).set(width=12.0).move_to([0,.65,0])
        self.play(Transform(svg,closed),FadeIn(highlight),run_time=.2)
        self.play(moving.animate.move_to(time_line.n2p(1.15)),run_time=1.5,rate_func=linear)
        opened=SVGMobject(str(HERE/'assets/circuit.svg')).set(width=12.0).move_to([0,.65,0])
        self.play(Transform(svg,opened),FadeOut(highlight),run_time=.2)
        self.play(moving.animate.move_to(time_line.n2p(1.4)),run_time=1,rate_func=linear)

    def plot_row(self,key,range_y,ypos,label,zoom=False):
        window=[1.15,1.26,.02] if zoom else [.8,1.4,.1]
        ticks=[1.15,1.18,1.22,1.26] if zoom else [.8,1,1.15,1.4]
        ax=Axes(x_range=window,y_range=range_y,x_length=10.7,y_length=1.15,tips=False,
            axis_config={'color':'#526C82','stroke_width':1,'font_size':20},
            x_axis_config={'include_numbers':key=='q_mvar','numbers_to_include':ticks,'decimal_number_config':{'num_decimal_places':2}},
            y_axis_config={'include_numbers':True}).move_to([.6,ypos,0])
        variable,unit=label.split(r'\ ')
        lab=VGroup(equation(variable,27),equation(unit,23)).arrange(DOWN,buff=.08).move_to([-5.95,ypos,0])
        curves=[]
        for engine,color in [('emt',TEAL),('rms',PURPLE)]:
            name=f'capacitive_{engine}_{key}';t=self.data[name+'_t'];value=self.data[name]
            mask=(t>=window[0])&(t<=window[1]);t=t[mask];value=value[mask]
            origin=ax.c2p(0,0)
            points=origin+t[:,None]*(ax.c2p(1,0)-origin)+value[:,None]*(ax.c2p(0,1)-origin)
            line=VMobject(color=color,stroke_width=2.5).set_points_as_corners(points)
            if engine=='rms':line=DashedVMobject(line,num_dashes=95,dashed_ratio=.65)
            curves.append(line)
        if zoom:
            band=Line(ax.c2p(1.15,range_y[0]),ax.c2p(1.15,range_y[1]),color=RED,stroke_width=1.3)
        else:
            band=Polygon(ax.c2p(1,range_y[0]),ax.c2p(1.15,range_y[0]),ax.c2p(1.15,range_y[1]),ax.c2p(1,range_y[1]),
                stroke_width=0,fill_color=RED,fill_opacity=.1)
        return ax,lab,band,curves

    def results(self):
        legend=VGroup(words('PSCAD EMT',21,TEAL),words('PSS/E RMS (dashed)',21,PURPLE),words('One-cycle windows • capacitive case',19,MUTED)).arrange(RIGHT,buff=.45).move_to([0,2.52,0])
        self.add(legend)
        rows=[self.plot_row('v_pu',[0,1.6,.5],1.48,r'V_{\mathrm{PCC}}\ (\mathrm{pu})'),
              self.plot_row('i_ka',[0,.3,.1],-.12,r'I_{\mathrm{STATCOM}}\ (\mathrm{kA})'),
              self.plot_row('q_mvar',[0,140,50],-1.72,r'Q_{\mathrm{STATCOM}}\ (\mathrm{MVAr})')]
        for ax,lab,band,curves in rows:self.add(band,ax,lab)
        self.play(FadeIn(VGroup(*[curve for row in rows for curve in row[3]])),run_time=1.2)
        self.add(equation(r't\ (\mathrm{s})',25).move_to([5.9,-2.68,0]))
        self.at(3)
        note=words('Current and reactive power track closely after window alignment.',21).move_to([0,-3.22,0])
        self.play(FadeIn(note),run_time=.5)
        self.at(7)
        detailed=[self.plot_row('v_pu',[0,1.6,.5],1.48,r'V_{\mathrm{PCC}}\ (\mathrm{pu})',True),
                  self.plot_row('i_ka',[0,.3,.1],-.12,r'I_{\mathrm{STATCOM}}\ (\mathrm{kA})',True),
                  self.plot_row('q_mvar',[0,140,50],-1.72,r'Q_{\mathrm{STATCOM}}\ (\mathrm{MVAr})',True)]
        def panel(row):
            ax,lab,band,curves=row
            return VGroup(band,ax,lab,*curves)
        # Cross-fade real samples into a narrower time view; never morph data values.
        self.play(*[FadeOut(panel(row)) for row in rows],
                  *[FadeIn(panel(row)) for row in detailed],run_time=.65)
        self.play(FadeOut(note),run_time=.2)
        note=words('Clearing and recovery — zoom with every recorded output sample',21,GOLD).move_to([0,-3.22,0])
        self.play(FadeIn(note),run_time=.3)
        self.at(11)
        pointer=Arrow([-1.5,2.25,0],detailed[0][0].c2p(1.166,1.5),color=GOLD,buff=.06,stroke_width=2.5,tip_length=.13)
        self.play(GrowArrow(pointer),run_time=.5)
        self.at(14)
        self.play(FadeOut(pointer),FadeOut(note),run_time=.2)
        note=words('Clearing voltage differs: network energy and angle tracking matter.',21,GOLD).move_to([0,-3.22,0])
        self.play(FadeIn(note),run_time=.4)

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
