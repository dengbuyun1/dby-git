from simglucose.patient.t1dpatient import T1DPatient, Action
import numpy as np
import time

p = T1DPatient.withName('adolescent#001')

print("=== Default params ===")
print('Init state:', p.state[0:5])
print('Init BG:', p.observation.Gsub)

# Change a param to force a new steady state
p._params['kp1'] *= 1.5

basal = p._params.u2ss * p._params.BW / 6000.0

print("\n=== After changing kp1 ===")
print('BG immediately after param change (no step):', p.observation.Gsub)

t0 = time.time()
print("\nBurn-in for 1440 mins...")
for _ in range(1440):
    p.step(Action(CHO=0, insulin=basal))

print('Burn-in state:', p.state[0:5])
print('Burn-in BG:', p.observation.Gsub)

# Force a reset but overriding init_state
new_init = p.state.copy()
p._init_state = new_init
p.reset()

print("\n=== After reset with new init_state ===")
print('After reset BG:', p.observation.Gsub)
