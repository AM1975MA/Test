from core24 import *

def main():
    d=pd.read_csv(OUT/'MONTHLY_DIAGNOSIS.csv').query('bps==15 and lag==0 and rule not in ["WF_ECONOMIC","WF_PRUDENT"]')
    labels=[];series=[]
    for r in RULES[1:]:
        for m in MARKETS:
            a=d[(d.rule==r)&(d.market==m)].sort_values('month');assert len(a)==78
            labels.append((m,r));series.append(np.log1p(a.new_return).to_numpy()-np.log1p(a.base_return).to_numpy())
    x=np.array(series).T;n=len(x);rng=np.random.default_rng(240025)
    ix=((rng.integers(0,n,(3000,7,1))+np.arange(12))%n).reshape(3000,-1)[:,:n]
    means=x.mean(0)*12;boot=x[ix].mean(1)*12;se=boot.std(0,ddof=1)
    assert np.all(se>0)
    centered=(boot-means)/se;critical=float(np.quantile(np.abs(centered).max(1),.95))
    rows=[dict(market=m,rule=r,annual_log_delta=float(means[j]),bootstrap_se=float(se[j]),family95_low=float(means[j]-critical*se[j]),family95_high=float(means[j]+critical*se[j]),critical=critical,comparisons=len(labels)) for j,(m,r) in enumerate(labels)]
    pd.DataFrame(rows).to_csv(OUT/'CONFIDENCE_FAMILY.csv',index=False)
    (OUT/'CONFIDENCE_METHOD.md').write_text('Diagnostica aggiunta dopo gli esiti, senza nuove varianti: intervalli simultanei approssimati max-|t| bootstrap, 33 confronti della famiglia U24 (11 regole x3 panieri), blocchi circolari12mesi, 3000 repliche condivise. Centro su media osservata, errore standard bootstrap; non è correzione completa dei test Perseo precedenti né probabilità futura. La breve serie78mesi limita la precisione. Critico95%: '+str(critical)+'\n')
    print(pd.DataFrame(rows).query('rule in ["PROFIT_RAMP","CONFIRM_RAMP"]').to_string(index=False))
if __name__=='__main__':main()
