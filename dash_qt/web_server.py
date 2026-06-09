"""DASH player — browser UI for control/monitor, mplayer for .264 playback."""

import http.server, json, os, sys, threading, subprocess, time, logging
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)
PORT=8088;B=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_st={'status':'idle','progress':0,'total':0,'speed':0,'bandwidth':0,'buffer':0}
_mplayer=None

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=B,**kw)
    def do_GET(self):
        p=urlparse(self.path).path
        if p in('/','/index.html'):self._h()
        elif p=='/api/start':self._s()
        elif p=='/api/status':self._j(_st)
        elif p=='/api/stop':self._stop()
        else:super().do_GET()
    def _h(self):self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.end_headers();self.wfile.write(HTML.encode())
    def _stop(self):
        global _mplayer
        if _mplayer:
            try:_mplayer.kill()
            except:pass
            _mplayer=None
        self._j({'status':'stopped'})
    def _s(self):
        global _st,_mplayer
        q=parse_qs(urlparse(self.path).query);u=q.get('url',[''])[0];t=q.get('strategy',['fixed'])[0]
        if not u:self._j({'error':'No URL'});return
        self._j({'status':'started'})
        if _mplayer:
            try:_mplayer.kill()
            except:pass
            _mplayer=None
        _st={'status':'parsing','progress':0,'total':0,'speed':0,'bandwidth':0,'buffer':0}
        threading.Thread(target=self._d,args=(u,t),daemon=True).start()
    def _d(self,url,stn):
        global _st,_mplayer;s=_st
        try:
            from ParseMpd import ParseMpd;from BufferManager import BufferManager;from strategy import create_strategy
            s['status']='parsing';p=ParseMpd();r=p.parse_mpd(url);tot=r['total_seq'];th=r['threshold'];s['total']=tot;s['status']='downloading'
            bu=r['base_url']
            if'192.168'in bu or'concert.itec'in bu:bu='http://127.0.0.1:8087/dataset/I/segs/360p/'
            ca=bu.split('//')[-1].replace('/','.',).replace(': ',',');bf=BufferManager(bu,ca);bf.buffer_length=10
            st=create_strategy(stn, quality=0)
            vn=url.split('/')[-1].replace('.mpd','')
            if not os.path.exists(vn):os.makedirs(vn)
            sb,spd,_=bf.download_init_segment(vn,r['data']);out=vn+'/out.264'
            for i in range(tot):
                ly=st.select_layer(i,spd,bf.buffer_list.qsize(),th)
                fl,spd,tm=bf.download_segment(ly,i,r['list_url'])
                bf.generate_h264(vn,i,fl,sb,out)
                try:bf.buffer_list.put_nowait({})
                except:pass
                st.update_state(bf.buffer_list.qsize(),spd)
                s['progress']=i+1;s['speed']=spd/1024/8;s['bandwidth']=spd/1024/8;s['buffer']=bf.buffer_list.qsize()
                # Start mplayer on segment 0
                if i==0:
                    import shutil
                    dstdir=B;src=out;dst=os.path.join(dstdir,'video.264')
                    shutil.copy2(src,dst)
                    _mplayer=subprocess.Popen(['/Users/yrj/bin/mplayer','-geometry','50%:50%','-really-quiet',dst])
            st.finalize();s['status']='done'
        except Exception as e:
            import traceback;traceback.print_exc();s['status']='error';s['error']=str(e)
    def _j(self,d):
        b=json.dumps(d).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Access-Control-Allow-Origin','*');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def log_message(self,*a):pass

HTML=r"""<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><title>DASH</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#c0c0c8;font-family:-apple-system,system-ui,sans-serif;height:100vh;display:flex}
#side{width:340px;background:#0f1119;border-right:1px solid #1a1a2e;padding:24px 20px;display:flex;flex-direction:column;gap:16px;overflow-y:auto}
h1{font-family:monospace;font-size:16px;letter-spacing:2px;color:#0f0;text-transform:uppercase;border-bottom:1px solid #1a1a2e;padding-bottom:12px}
h1 span{color:#666}
.f{display:flex;flex-direction:column;gap:4px}
.f label{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#555}
.f input,.f select{background:#161822;border:1px solid #1a1a2e;color:#ccc;padding:10px 12px;font-size:13px;border-radius:2px;outline:none}
.f input:focus,.f select:focus{border-color:#0f0}
button{background:transparent;border:1px solid #0f0;color:#0f0;font-family:monospace;font-size:14px;letter-spacing:2px;text-transform:uppercase;padding:12px;cursor:pointer;border-radius:2px}
button:hover{background:rgba(0,255,0,0.05)}
button:disabled{border-color:#333;color:#555;cursor:not-allowed}
#stop{border-color:#f44;color:#f44}
#stop:hover{background:rgba(255,68,68,0.05)}
#bar{height:2px;background:#1a1a2e;overflow:hidden}
#bar div{height:100%;background:#0f0;width:0;transition:width .3s}
#st{font-family:monospace;font-size:11px;letter-spacing:1px;color:#0f0;text-align:center;text-transform:uppercase}
.d{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.c{background:#161822;border:1px solid #1a1a2e;padding:10px 12px}
.c .l{font-size:9px;color:#555;text-transform:uppercase;letter-spacing:1px}
.c .v{font-family:monospace;font-size:16px;color:#0f0}
</style></head><body>
<div id="side">
<h1>DASH<span>·mplayer</span></h1>
<div class="f"><label>MPD Endpoint</label><input id="url" value="http://127.0.0.1:8087/dataset/mpd/BBB-I-360p.mpd"></div>
<div class="f"><label>Strategy</label><select id="strat"><option selected>fixed</option></select></div>
<button id="go" onclick="go()">▶ Stream</button>
<button id="stop" onclick="stop()">⏹ Stop</button>
<div id="bar"><div id="fill"></div></div>
<div id="st">IDLE</div>
<div class="d">
<div class="c"><div class="l">Speed</div><div class="v" id="spd">--</div></div>
<div class="c"><div class="l">Bandwidth</div><div class="v" id="bw">--</div></div>
<div class="c"><div class="l">Buffer</div><div class="v" id="buf">--</div></div>
<div class="c"><div class="l">Segment</div><div class="v" id="seg">--</div></div>
</div></div>
<script>
function go(){
 var u=document.getElementById('url').value.trim();if(!u)return;
 var b=document.getElementById('go');b.disabled=true;b.textContent='CONNECTING...';
 document.getElementById('st').textContent='INIT';
 fetch('/api/start?url='+encodeURIComponent(u)+'&strategy='+document.getElementById('strat').value)
  .then(r=>r.json()).then(d=>{if(d.error)throw Error(d.error);poll()})
  .catch(e=>{b.disabled=false;b.textContent='▶ Stream'})
}
function stop(){fetch('/api/stop');document.getElementById('go').disabled=false;document.getElementById('go').textContent='▶ Stream';document.getElementById('st').textContent='STOPPED'}
function poll(){
 fetch('/api/status').then(r=>r.json()).then(s=>{
  document.getElementById('st').textContent=s.status.toUpperCase();
  if(s.total>0){document.getElementById('fill').style.width=(s.progress/s.total*100).toFixed(1)+'%';document.getElementById('seg').textContent=s.progress+' / '+s.total}
  if(s.speed>0){document.getElementById('spd').textContent=(s.speed>1e3?(s.speed/1e3).toFixed(1)+' Mbps':s.speed.toFixed(0)+' kbps');document.getElementById('bw').textContent=(s.bandwidth>1e3?(s.bandwidth/1e3).toFixed(1)+' Mbps':(s.bandwidth||s.speed).toFixed(0)+' kbps')}
  if(s.buffer>0)document.getElementById('buf').textContent=s.buffer+' / 10';
  if(s.status==='done'||s.status==='error'){document.getElementById('go').disabled=false;document.getElementById('go').textContent='▶ Stream'}
  else{setTimeout(poll,400)}
 }).catch(()=>setTimeout(poll,1000))}
</script></body></html>"""

def main():
    import signal;signal.signal(signal.SIGCHLD,signal.SIG_DFL)
    s=http.server.HTTPServer(('127.0.0.1',PORT),H)
    print(f"http://127.0.0.1:{PORT}")
    try:s.serve_forever()
    except KeyboardInterrupt:print("Done");s.shutdown()
if __name__=='__main__':main()
