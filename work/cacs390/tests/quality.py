import numpy as np, subprocess, struct, warnings, glob, sys
warnings.filterwarnings('ignore')
def wav(path, x, rate, bits=16):
    x=np.atleast_2d(x.T).T if x.ndim==1 else x
    ch=x.shape[1]
    if bits==16: data=(np.clip(x,-1,1)*32767).astype('<i2').tobytes(); fmt=1
    elif bits==24:
        i=(np.clip(x,-1,1)*8388607).astype('<i4'); b=i.view(np.uint8).reshape(-1,4)[:,:3]; data=b.tobytes(); fmt=1
    elif bits==32: data=x.astype('<f4').tobytes(); fmt=3
    elif bits==8: data=((np.clip(x,-1,1)*127)+128).astype('u1').tobytes(); fmt=1
    ba=ch*bits//8
    h=b'RIFF'+struct.pack('<I',36+len(data))+b'WAVE'+b'fmt '+struct.pack('<IHHIIHH',16,fmt,ch,rate,rate*ba,ba,bits)+b'data'+struct.pack('<I',len(data))
    open(path,'wb').write(h+data)
def dec(p, ch=1):
    r=subprocess.run(['ffmpeg','-v','error','-i',p,'-f','f32le','-acodec','pcm_f32le','-'],capture_output=True)
    y=np.frombuffer(r.stdout,dtype='<f4'); return y.reshape(-1,ch)
def snr_of(X,y):
    n=len(X); yy=y[128:128+n]; e=X[:len(yy)]-yy
    return 10*np.log10((X**2).sum()/max(1e-30,(e**2).sum())) if (X**2).sum()>0 else float('nan')
def synth():
    rs=np.random.RandomState(0); out=[]
    t=np.arange(int(44100*2.5))/44100
    chirp=0.5*np.sin(2*np.pi*(200*t+2000*t**2))
    out.append(('stereo44k', np.stack([chirp, 0.3*rs.randn(len(t))*np.exp(-t)],1), 44100, 16))
    t=np.arange(48000*3)/48000
    out.append(('mono48k_24bit', 0.7*np.sin(2*np.pi*440*t)*np.sin(2*np.pi*1.3*t), 48000, 24))
    out.append(('fullscale_square', np.sign(np.sin(2*np.pi*100*np.arange(32000)/32000))*0.999, 32000, 16))
    out.append(('long60s', 0.3*np.sin(2*np.pi*300*np.arange(32000*60)/32000)+0.05*rs.randn(32000*60), 32000, 16))
    return out
kb=sys.argv[1] if len(sys.argv)>1 else '96'
for name,x,rate,bits in synth():
    wav('/tmp/%s.wav'%name, x, rate, bits)
    r=subprocess.run(['./hca_cli','/tmp/%s.wav'%name,'/tmp/%s.hca'%name, kb],capture_output=True,text=True)
    X=np.atleast_2d(x.T).T if x.ndim==1 else x
    print('%-18s SNR %.1f dB  (%s)'%(name, snr_of(X, dec('/tmp/%s.hca'%name, X.shape[1])), r.stdout.strip().split(', mean')[1]))
src=sorted(glob.glob('/work/youngvoice/dec_us/*.wav'))
for kbps in (64, 85.25, 128):
    s=[]
    for p in src:
        x=dec(p)[:,0]
        if (x**2).sum()==0: continue
        subprocess.run(['./hca_cli',p,'/tmp/t.hca',str(kbps)],capture_output=True,text=True)
        s.append(snr_of(x, dec('/tmp/t.hca')[:,0]))
    print('voice', kbps,'kbps: SNR min %.1f median %.1f max %.1f'%(min(s),np.median(s),max(s)))
