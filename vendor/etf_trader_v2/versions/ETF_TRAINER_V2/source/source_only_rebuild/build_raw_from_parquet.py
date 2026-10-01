from __future__ import annotations
from pathlib import Path
import argparse, ctypes, struct, json, hashlib, shutil
import numpy as np
import pandas as pd
from thrift.transport.TTransport import TMemoryBuffer
from thrift.protocol.TCompactProtocol import TCompactProtocol
from thrift.Thrift import TType

FIELDS=("OPEN","HIGH","LOW","CLOSE","VOLUME")
OUT_NAMES={"OPEN":"Open","HIGH":"High","LOW":"Low","CLOSE":"Close","VOLUME":"Volume"}
TT={v:k for k,v in vars(TType).items() if k.isupper() and isinstance(v,int)}

def read_val(p,t):
    if t==TType.BOOL:return p.readBool()
    if t==TType.BYTE:return p.readByte()
    if t==TType.I16:return p.readI16()
    if t==TType.I32:return p.readI32()
    if t==TType.I64:return p.readI64()
    if t==TType.DOUBLE:return p.readDouble()
    if t==TType.STRING:return p.readBinary()
    if t==TType.STRUCT:return read_struct(p)
    if t==TType.LIST:
        et,n=p.readListBegin();v=[read_val(p,et) for _ in range(n)];p.readListEnd();return ('LIST',TT.get(et,et),v)
    if t==TType.SET:
        et,n=p.readSetBegin();v=[read_val(p,et) for _ in range(n)];p.readSetEnd();return ('SET',TT.get(et,et),v)
    if t==TType.MAP:
        kt,vt,n=p.readMapBegin();v=[(read_val(p,kt),read_val(p,vt)) for _ in range(n)];p.readMapEnd();return ('MAP',TT.get(kt,kt),TT.get(vt,vt),v)
    raise ValueError(t)

def read_struct(p):
    p.readStructBegin();out=[]
    while True:
        _,t,fid=p.readFieldBegin()
        if t==TType.STOP:break
        out.append((fid,TT.get(t,t),read_val(p,t)));p.readFieldEnd()
    p.readStructEnd();return out

def fd(s):return {fid:v for fid,t,v in s}

lib=ctypes.CDLL('libzstd.so.1')
lib.ZSTD_decompress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
lib.ZSTD_decompress.restype=ctypes.c_size_t
lib.ZSTD_isError.argtypes=[ctypes.c_size_t];lib.ZSTD_isError.restype=ctypes.c_uint
lib.ZSTD_getErrorName.argtypes=[ctypes.c_size_t];lib.ZSTD_getErrorName.restype=ctypes.c_char_p

def zstd(src,n):
    out=ctypes.create_string_buffer(n);inp=ctypes.create_string_buffer(src)
    r=lib.ZSTD_decompress(out,n,inp,len(src))
    if lib.ZSTD_isError(r):raise RuntimeError(lib.ZSTD_getErrorName(r).decode())
    if r!=n:raise RuntimeError(f'zstd output {r} != expected {n}')
    return out.raw[:r]

def varint(data,pos):
    x=0;s=0
    while True:
        b=data[pos];pos+=1;x|=(b&0x7f)<<s
        if not (b&0x80):return x,pos
        s+=7

def unpack_bits(data,bw,count):
    vals=[];bit=0;mask=(1<<bw)-1 if bw else 0
    for _ in range(count):
        bi=bit>>3;off=bit&7;nbytes=(off+bw+7)//8
        ch=int.from_bytes(data[bi:bi+nbytes],'little') if nbytes else 0
        vals.append((ch>>off)&mask if bw else 0);bit+=bw
    return vals,(bit+7)//8

def hybrid(data,bw,expected):
    vals=[];pos=0
    while len(vals)<expected:
        h,pos=varint(data,pos)
        if h&1:
            groups=h>>1;n=groups*8;nbytes=groups*bw
            vv,_=unpack_bits(data[pos:pos+nbytes],bw,n);pos+=nbytes;vals.extend(vv)
        else:
            n=h>>1;nbytes=(bw+7)//8;v=int.from_bytes(data[pos:pos+nbytes],'little') if nbytes else 0;pos+=nbytes;vals.extend([v]*n)
    return vals[:expected],pos

class ParquetFlat:
    def __init__(self,path):
        self.path=Path(path);self.b=self.path.read_bytes();fl=int.from_bytes(self.b[-8:-4],'little')
        self.meta=fd(read_struct(TCompactProtocol(TMemoryBuffer(self.b[-8-fl:-8]))))
        self.schema=[fd(x) for x in self.meta[2][2]][1:]
        rgs=self.meta[4][2]
        if len(rgs)!=1:raise RuntimeError('expected one row group')
        self.cols=fd(rgs[0])[1][2];self.n=int(self.meta[3])
        self.names=[s[4].decode() for s in self.schema]
    def decode_col(self,idx):
        md=fd(fd(self.cols[idx])[3]);typ=md[1];codec=md[4]
        starts=[x for x in (md.get(11),md.get(9)) if x is not None];pos=min(starts);end=pos+md[7]
        dictionary=None;out=[]
        while pos<end:
            tr=TMemoryBuffer(self.b[pos:end]);h=fd(read_struct(TCompactProtocol(tr)));hl=tr.cstringio_buf.tell()
            body=self.b[pos+hl:pos+hl+h[3]];raw=zstd(body,h[2]) if codec==6 else body;pos+=hl+h[3]
            if h[1]==2:
                dh=fd(h[7]);dn=dh[1]
                if typ==5:dictionary=list(struct.unpack('<'+'d'*dn,raw[:8*dn]))
                elif typ==2:dictionary=list(struct.unpack('<'+'q'*dn,raw[:8*dn]))
                else:raise NotImplementedError(('type',typ))
            elif h[1]==0:
                ph=fd(h[5]);n=ph[1];enc=ph[2]
                dl=int.from_bytes(raw[:4],'little');defs,_=hybrid(raw[4:4+dl],1,n);rest=raw[4+dl:]
                nn=sum(defs)
                if enc==8:
                    bw=rest[0];ids,_=hybrid(rest[1:],bw,nn);it=iter(ids)
                    out.extend(dictionary[next(it)] if d else None for d in defs)
                elif enc==0:
                    if typ==5:vals=list(struct.unpack('<'+'d'*nn,rest[:8*nn]))
                    elif typ==2:vals=list(struct.unpack('<'+'q'*nn,rest[:8*nn]))
                    else:raise NotImplementedError(('plain type',typ))
                    it=iter(vals);out.extend(next(it) if d else None for d in defs)
                else:raise NotImplementedError(('encoding',enc))
            else:raise NotImplementedError(('page type',h[1]))
        if len(out)!=self.n:raise RuntimeError((self.path.name,idx,len(out),self.n))
        return out

def sha256(p):
    h=hashlib.sha256();
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--matrix-dir',default='/mnt/data/etf_cleanroom/raw_matrix')
    ap.add_argument('--output',default='/mnt/data/etf_cleanroom/raw_ticker_csv')
    ap.add_argument(
        '--expected-manifest',
        default='/mnt/data/etf_cleanroom/postfix_bundle/ETF_TRADER_POSTFIX_CURRENT_RAW_REPLAY_20260924/raw/manifest.json',
        help="historical full-file parity manifest; use 'none' for prospective extensions",
    )
    args=ap.parse_args()
    root=Path(args.matrix_dir);out=Path(args.output)
    if out.exists():shutil.rmtree(out)
    out.mkdir()
    mats={};names=None;dates=None
    for f in FIELDS:
        q=ParquetFlat(root/f'{f}.parquet')
        if names is None:names=q.names[:-1]
        elif q.names[:-1]!=names:raise RuntimeError('column mismatch')
        d=q.decode_col(q.names.index('date'))
        if dates is None:dates=pd.to_datetime(np.asarray(d,dtype='int64'))
        elif not dates.equals(pd.to_datetime(np.asarray(d,dtype='int64'))):raise RuntimeError('date mismatch')
        arr={}
        for i,t in enumerate(names):arr[t]=q.decode_col(i)
        mats[f]=arr;print('decoded',f,len(names),len(dates),flush=True)
    cat={t:f'C{(i//25)+1:02d}_'+['US_BROAD_STYLE','US_SECTOR_THEME','DEVELOPED_GLOBAL','EMERGING','BONDS_CASH_CREDIT','REAL_ASSETS'][i//25] for i,t in enumerate(names)}
    usable=[t for t in names if t!='PIN']
    um=pd.DataFrame({'ticker':sorted(usable)})
    um['macro_category']=um['ticker'].map(cat)
    um.to_csv(out/'universe.csv',index=False)
    files={}
    for j,t in enumerate(usable,1):
        z=pd.DataFrame({'date':dates,**{OUT_NAMES[f]:mats[f][t] for f in FIELDS}})
        vals=z[['Open','High','Low','Close','Volume']].apply(pd.to_numeric,errors='coerce')
        good=np.isfinite(vals).all(axis=1);z=z.loc[good].copy()
        if z.empty:continue
        if (z[['Open','High','Low','Close']]<=0).any().any() or (z['Volume']<0).any():raise RuntimeError('invalid '+t)
        bad=(z.Low>z[['Open','Close']].min(axis=1)+1e-8)|(z.High<z[['Open','Close']].max(axis=1)-1e-8)
        if bad.any():raise RuntimeError(f'ohlc {t} {bad.sum()}')
        p=out/f'{t}.csv';z.to_csv(p,index=False,float_format='%.17g')
        files[p.name]={'sha256':sha256(p),'rows':len(z),'start':str(z.date.min().date()),'end':str(z.date.max().date())}
        if j%25==0:print('csv',j,flush=True)
    man={'status':'RAW_MATRIX_TO_TICKER_CSV','productive_data_only':True,'source_sha256':{f'{f}.parquet':sha256(root/f'{f}.parquet') for f in FIELDS},'tickers':len(files),'files':files}
    (out/'manifest.json').write_text(json.dumps(man,indent=2)+'
')
    if str(args.expected_manifest).lower() not in {'none','skip',''}:
        expected_manifest=Path(args.expected_manifest)
        if not expected_manifest.is_file():
            raise FileNotFoundError(expected_manifest)
        exp=json.load(open(expected_manifest))
        mism=[]
        for k,v in exp['files'].items():
            got=files.get(k)
            if got is None or got['sha256']!=v['sha256']:mism.append((k,v['sha256'],None if got is None else got['sha256']))
        extra=sorted(set(files)-set(exp['files']))
        print(json.dumps({'tickers':len(files),'expected':len(exp['files']),'mismatches':len(mism),'extra':extra[:5],'first_mismatches':mism[:5]},indent=2))
    else:
        print(json.dumps({'tickers':len(files),'historical_full_file_parity':'SKIPPED_FOR_PROSPECTIVE_EXTENSION'},indent=2))

if __name__=='__main__':main()
