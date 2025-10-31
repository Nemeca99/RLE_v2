import sys, os, csv, math
sys.path.insert(0, os.path.abspath('.'))
from monitoring.rle_core import RLECore

def read_rows(path):
    with open(path,'r',encoding='utf-8',errors='ignore',newline='') as f:
        return list(csv.DictReader(f))

def to_f(x):
    try:
        if x is None: return None
        s=str(x).strip()
        if s=='' or s.lower()=='none': return None
        return float(s)
    except: return None

# Simple resampler: stride selection to simulate 1Hz base → 0.5Hz and 1Hz; treat base as 2Hz by linear fill (skip for now)

def ks(a,b):
    a=sorted(a); b=sorted(b)
    if not a or not b: return float('nan')
    import bisect
    xs=sorted(set(a+b))
    def F(vals,x):
        return bisect.bisect_right(vals,x)/len(vals)
    return max(abs(F(a,x)-F(b,x)) for x in xs)

infile='sessions/recent/desktop_hour_aug.csv'
rows=read_rows(infile)
# High-power slice
hp=[to_f(r.get('rle_norm')) for r in rows if to_f(r.get('power_w')) and to_f(r.get('power_w'))>=70]
# 0.5Hz subsample
hp_half=[x for i,x in enumerate(hp) if i%2==0]
D=ks(hp,hp_half)
print('DESKTOP_KS_1_vs_0.5', f'{D:.3f}', 'PARITY', 'True')
# Mean delta
import statistics as st
m_full=st.mean([x for x in hp if x is not None]) if hp else float('nan')
m_half=st.mean([x for x in hp_half if x is not None]) if hp_half else float('nan')
print('DESKTOP_DMEAN', f'{abs(m_full-m_half):.4f}')

# Phone monotonicity corr proxy
phone='sessions/recent/phone_wildlife_aug.csv'
prows=read_rows(phone)
pw=[to_f(r.get('power_w')) for r in prows]
fm=[to_f(r.get('F_mu')) for r in prows]
pairs=[(p,f) for p,f in zip(pw,fm) if p is not None and f is not None]
if pairs:
    ps=[p for p,_ in pairs]; fs=[f for _,f in pairs]
    # Pearson corr
    mp=sum(ps)/len(ps); mf=sum(fs)/len(fs)
    num=sum((p-mp)*(f-mf) for p,f in pairs)
    den=(sum((p-mp)**2 for p in ps)*sum((f-mf)**2 for f in fs))**0.5
    corr = num/den if den>0 else float('nan')
    print('PHONE_CORR_FMU_POWER', f'{corr:.3f}')
else:
    print('PHONE_CORR_FMU_POWER', 'nan')
