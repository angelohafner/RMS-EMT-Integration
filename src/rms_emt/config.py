"""Strict study configuration and portable JSON helpers."""
import hashlib
import json
import math
from pathlib import Path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_config(path):
    c = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    validate_config(c)
    return c


def validate_config(c):
    if c.get('schema_version') != 1:
        raise ValueError('Configuration schema_version must be 1.')
    for section, keys in {
        'grid': ['base_mva','voltage_kv_ll','frequency_hz','short_circuit_mva','xr_ratio','slack_voltage_pu'],
        'statcom': ['rating_mvar','droop_pu','current_tau_s','voltage_floor_pu'],
        'fault': ['start_s','duration_s','resistance_ohm'],
        'simulation': ['duration_s','time_step_us','sample_step_us','timeout_s'],
    }.items():
        for key in keys:
            value = c[section][key]
            if not isinstance(value, (int,float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{section}.{key} must be finite and positive.')
    s, f, st = c['simulation'], c['fault'], c['statcom']
    for value in [c['load']['p_mw'], c['load']['q_mvar'], st['q_initial_mvar'],st['enable_time_s']]:
        if not math.isfinite(value):
            raise ValueError('Load, setpoint and enable time must be finite.')
    if min(c['load'].values()) < 0:
        raise ValueError('The demonstration supports a passive P>=0, Q>=0 load.')
    if not math.isfinite(c['load']['capacitance_nf']) or c['load']['capacitance_nf']<=0:
        raise ValueError('A positive finite PCC capacitance is required for the EMT switching transient.')
    if abs(st['q_initial_mvar']) > st['rating_mvar']:
        raise ValueError('Initial STATCOM Q exceeds the nominal MVAr rating.')
    if st['enable_time_s'] < 0 or st['enable_time_s']+10*st['current_tau_s'] >= f['start_s']:
        raise ValueError('Allow at least ten current time constants before the fault.')
    if not 0 < st['voltage_floor_pu'] < 1:
        raise ValueError('voltage_floor_pu must be between zero and one.')
    if f['start_s'] + f['duration_s'] + 5/c['grid']['frequency_hz'] >= s['duration_s']:
        raise ValueError('Simulation must cover the fault and at least five post-fault cycles.')
    dt=s['time_step_us']*1e-6; sample=s['sample_step_us']*1e-6
    if sample < dt or not math.isclose(sample/dt,round(sample/dt),abs_tol=1e-8):
        raise ValueError('sample_step_us must be an integer multiple of time_step_us.')
    if sample*c['grid']['frequency_hz'] > .02 or dt > st['current_tau_s']/20:
        raise ValueError('Insufficient samples per cycle or current-control time constant.')
    a,b=s['prefault_window_s']
    if not st['enable_time_s']+10*st['current_tau_s'] <= a < b < f['start_s']:
        raise ValueError('Pre-fault window must be settled and strictly before the fault.')
    if b-a < 3/c['grid']['frequency_hz']:
        raise ValueError('Pre-fault comparison requires at least three cycles.')
    if c['pscad']['version'] != '5.1.0':
        raise ValueError('This adapter targets PSCAD 5.1.0; explicitly qualify other releases.')
    if c.get('rms',{}).get('enabled'):
        from .dynamic import validate_rms_settings
        validate_rms_settings(c)
        if c['comparison']['rms_csv'] or c['comparison']['rms_metadata']:
            raise ValueError('Choose native RMS generation or supplied RMS channels, not both.')
