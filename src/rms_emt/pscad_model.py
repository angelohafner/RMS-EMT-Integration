"""Build a native EMT network with the documented PSCAD Component Wizard API.

Only the terminal STATCOM control is a user-defined component. Grid, load,
fault switches and measurements use installed master-library definitions.
"""
import math


CONTROL_SCRIPT = '''#BEGIN
      ENABCCIN($A,$SS) = .TRUE.
      ENABCCIN($B,$SS) = .TRUE.
      ENABCCIN($C,$SS) = .TRUE.
#ENDBEGIN
#STORAGE REAL:4
#LOCAL INTEGER K
#LOCAL REAL VA0
#LOCAL REAL VB0
#LOCAL REAL VC0
#LOCAL REAL ALPHA
#LOCAL REAL BETA
#LOCAL REAL THETA
#LOCAL REAL VDNEW
#LOCAL REAL VQNEW
#LOCAL REAL MAGN
#LOCAL REAL TARGET
#LOCAL REAL PEAK
#LOCAL REAL ANG
      K = NSTORF
      NSTORF = NSTORF + 4
      IF (TIMEZERO) THEN
        STORF(K) = 0.0
        STORF(K+1) = 0.0
        STORF(K+2) = 0.0
        STORF(K+3) = 0.0
      ENDIF
      VA0 = $VDC:A:0
      VB0 = $VDC:B:0
      VC0 = $VDC:C:0
      ALPHA = (2.0*VA0-VB0-VC0)/3.0
      BETA = (VB0-VC0)/SQRT(3.0)
      THETA = TWO_PI*$Freq*TIME
      VDNEW = ALPHA*COS(THETA)+BETA*SIN(THETA)
      VQNEW = -ALPHA*SIN(THETA)+BETA*COS(THETA)
      STORF(K) = STORF(K)+(1.0-EXP(-DELT/0.01))*
     + (VDNEW-STORF(K))
      STORF(K+1) = STORF(K+1)+(1.0-EXP(-DELT/0.01))*
     + (VQNEW-STORF(K+1))
      MAGN = SQRT(STORF(K)**2+STORF(K+1)**2)
      $Vmeas = MAGN/($Vbase*SQRT(2.0/3.0))
      IF ($Vmeas .GT. $Vfloor) THEN
        STORF(K+3) = ATAN2(STORF(K+1),STORF(K))
      ENDIF
      TARGET = $Iq0+($Vop-$Vmeas)/$Droop
      TARGET = MAX(-1.0,MIN(1.0,TARGET))
      IF (TIME .LT. $Enable) TARGET = 0.0
      STORF(K+2) = STORF(K+2)+(1.0-EXP(-DELT/$Tau))*
     + (TARGET-STORF(K+2))
      $Iq = MAX(-1.0,MIN(1.0,STORF(K+2)))
! Advance the phase estimate by one electrical solution step.
      ANG = THETA+STORF(K+3)+TWO_PI*$Freq*DELT
      PEAK = SQRT(2.0)*$Ibase*$Iq
      $Ia = PEAK*SIN(ANG)
      $Ib = PEAK*SIN(ANG-TWO_PI/3.0)
      $Ic = PEAK*SIN(ANG+TWO_PI/3.0)
      CCIN($A,$SS) = CCIN($A,$SS)+$Ia
      CCIN($B,$SS) = CCIN($B,$SS)+$Ib
      CCIN($C,$SS) = CCIN($C,$SS)+$Ic
'''


def build_model(app, project_path, c, op):
    from mhi.pscad.wizard import UserDefnWizard
    from mhi.pscad.types import Signal
    project=app.create_case(str(project_path))
    project.parameters(time_duration=c['simulation']['duration_s'],
        time_step=c['simulation']['time_step_us'],sample_step=c['simulation']['sample_step_us'],
        PlotType='OUT',output_filename='emt.out',StartType=0,
        description='Sequential RMS EMT | averaged STATCOM terminal model')
    canvas=project.canvas('Main')
    canvas.parameters(size='100X100')

    def xy(component, name):
        p=component.port(name)
        if p is None: raise RuntimeError(f'Missing port {name} on {component.defn_name}')
        return (p.x,p.y)

    def wire(a,b):
        if a==b: return
        if a[0]==b[0] or a[1]==b[1]: canvas.create_wire(a,b)
        else: canvas.create_wire(a,(b[0],a[1]),b)

    def ground(node):
        canvas.create_component('master:ground',node[0],node[1])

    def output_from_label(name,unit,x,y,datatype=2):
        lab=canvas.create_component('master:datalabel',x,y,Name=name,datatype=datatype)
        channel=canvas.create_component('master:pgb',x+4,y,Name=name,Units=unit,
                                         Min=-500.,Max=500.,Group='RMS_EMT')
        lp=next(iter(lab.ports().values()));cp=next(iter(channel.ports().values()))
        wire((lp.x,lp.y),(cp.x,cp.y))

    wizard=UserDefnWizard('AveragedSTATCOM')
    wizard.description='Current limited reactive terminal model; ideal frequency reference; no PWM or DC link'
    for ph,y in [('A',-4),('B',0),('C',4)]: wizard.port.electrical(-6,y,ph)
    for signal,y in [('Ia',-6),('Ib',-4),('Ic',-2),('Iq',0),('Vmeas',2)]:
        wizard.port.output(6,y,signal,Signal.REAL)
    wizard.graphics.rectangle(-5,-7,5,7)
    wizard.graphics.text('AVERAGED STATCOM',0,4)
    wizard.graphics.text(f"{c['statcom']['rating_mvar']:g} MVAr nominal",0,6)
    cat=wizard.category.add('Electrical and control')
    params={'Freq':op['frequency_hz'],'Vbase':op['voltage_kv_ll'],
            'Vop':op['pcc_voltage_pu'],'Ibase':op['rated_current_ka'],
            'Iq0':op['iq_initial_pu'],'Droop':c['statcom']['droop_pu'],
            'Tau':c['statcom']['current_tau_s'],'Vfloor':c['statcom']['voltage_floor_pu'],
            'Enable':c['statcom']['enable_time_s']}
    for key,val in params.items(): cat.real(key,value=val,description=key)
    wizard.script['Dsdyn']=CONTROL_SCRIPT
    stat=canvas.create_component(wizard.create_definition(project),70,32,Name='STATCOM',**params)
    # A fixed voltage source uses the extracted R; three separate L branches complete Z1.
    source=canvas.create_component('master:source3',10,20,Name='THEVENIN',View=0,
        Type=1,Ctrl=0,Imp=0,Term=0,R1s=op['r_ohm'],Vm=op['voltage_kv_ll'],
        MVA=op['base_mva'],F=op['frequency_hz'],F0=op['frequency_hz'],
        Es=op['source_kv_ll'],Ph=op['source_phase_deg'],Tc=.05,TcTyp=1)
    ground(xy(source,'N'))
    channels=[]
    for idx,ph in enumerate('ABC'):
        y=12+idx*12
        ind=canvas.create_component('master:inductor',22,y,Name='GRID_L_'+ph,L=op['l_h'])
        meter=canvas.create_component('master:ammeter',28,y,Name='Ig'+ph.lower()+'_kA')
        source_node=xy(source,ph);ind_node=xy(ind,'A');route_x=15+idx*2
        canvas.create_wire(source_node,(route_x,source_node[1]),(route_x,y),ind_node)
        wire(xy(ind,'B'),xy(meter,'N1'))
        node=(40,y);wire(xy(meter,'N2'),node)
        volt=canvas.create_component('master:voltmetergnd',40,y,Name='V'+ph.lower()+'_kV')
        wire(node,xy(volt,'N1'))
        if op['load_r_ohm'] is not None:
            res=canvas.create_component('master:resistor',46,y+2,Name='LOAD_R_'+ph,R=op['load_r_ohm'])
            wire(node,xy(res,'A'));ground(xy(res,'B'))
        if op['load_l_h'] is not None:
            lind=canvas.create_component('master:inductor',46,y+5,Name='LOAD_L_'+ph,L=op['load_l_h'])
            wire(node,xy(lind,'A'));ground(xy(lind,'B'))
        capacitor=canvas.create_component('master:capacitor',46,y+8,Name='PCC_C_'+ph,
                    C=f"{op['pcc_capacitance_f']*1e6:.12g} [uF]")
        wire(node,xy(capacitor,'A'));ground(xy(capacitor,'B'))
        fault=canvas.create_component('master:fault_sw',54,y+10,Name='FaultOn',OpCur=1,
                ROn=c['fault']['resistance_ohm'],ROff=1e9,Iflt='If'+ph.lower()+'_kA')
        wire(node,xy(fault,'A'));ground(xy(fault,'B'))
        # Route to controller at separate phase elevations; avoid incidental junctions.
        end=xy(stat,ph)
        wire(node,(60+idx,y));wire((60+idx,y),(60+idx,end[1]));wire((60+idx,end[1]),end)
        channels.extend([('V'+ph.lower()+'_kV','kV'),('Ig'+ph.lower()+'_kA','kA'),('If'+ph.lower()+'_kA','kA')])
    for sig,label in [('Ia','Isa_kA'),('Ib','Isb_kA'),('Ic','Isc_kA'),('Iq','Iq_pu'),('Vmeas','Vmeas_pu')]:
        pos=xy(stat,sig)
        lab=canvas.create_component('master:datalabel',pos[0]+2,pos[1],Name=label)
        lp=next(iter(lab.ports().values()));wire(pos,(lp.x,lp.y))
        channels.append((label,'kA' if sig in ['Ia','Ib','Ic'] else 'pu'))
    timer=canvas.create_component('master:tfault',15,58,TF=c['fault']['start_s'],DF=c['fault']['duration_s'],REP=0)
    pos=xy(timer,'Y')
    lab=canvas.create_component('master:datalabel',pos[0]-3,pos[1],Name='FaultOn',datatype=1)
    lp=next(iter(lab.ports().values()));wire(pos,(lp.x,lp.y))
    for idx,(label,unit) in enumerate(channels):
        output_from_label(label,unit,10+idx//8*24,66+idx%8*3)
    output_from_label('FaultOn','bool',58,66,1)
    project.save()
    return project
