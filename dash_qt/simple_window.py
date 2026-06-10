"""SVC-DASH Player — pause/stop/reload, timer from main thread."""

import os, time, threading, queue, urllib.request, subprocess, traceback
from PySide6.QtWidgets import QMainWindow, QSplitter, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage
from dash_qt.simple_control import SimpleControl
from dash_qt.video_widget import VideoWidget


class SimpleWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._seg_buf = None; self._frame_buf = None; self._ffmpeg_procs = []
        self._w=640;self._h=360;self._fs=self._w*self._h*3
        self._dl_count=0;self._start_seg=0;self._playing_seg=0;self._frame_count=0;self._paused=True;self._done=False;self._stopped=False;self._dl_finished=False;self._player_done=False
        self._msgq = queue.Queue()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("SVC-DASH Player");self.setMinimumSize(1000,560);self.resize(1200,680)
        self.menuBar().addMenu("&File").addAction("&Quit",self.close,Qt.CTRL|Qt.Key_Q)
        s=QSplitter(Qt.Horizontal);self.control=SimpleControl();s.addWidget(self.control)
        self._video=VideoWidget();s.addWidget(self._video)
        s.setSizes([340,1020]);s.setStretchFactor(0,0);s.setStretchFactor(1,1)
        self.setCentralWidget(s)
        self.control.btn_start.clicked.connect(self._start)
        self.control.btn_pause.clicked.connect(self._toggle_pause)
        self.control.btn_stop.clicked.connect(self._stop)
        self.control.seek_slider.sliderReleased.connect(self._seek)
        self._poll=QTimer(self);self._poll.setInterval(200);self._poll.timeout.connect(self._poll_all)
        self._ft=QTimer(self);self._ft.setInterval(40);self._ft.timeout.connect(self._show_frame)

    def _poll_all(self):
        try:
            while True:
                m=self._msgq.get_nowait()
                if m=='start_ft' and not self._ft.isActive():self._ft.start()
        except queue.Empty: pass
        if self._seg_buf is not None:
            qsz = self._seg_buf.qsize() + (self._frame_buf.qsize()//48 if self._frame_buf else 0)
            if self._dl_finished and qsz==0:
                self.control.update_stats(buffer_size=0,segment=self._dl_count,status="Finishing...")
            else:
                self.control.update_stats(buffer_size=min(qsz,10),segment=self._dl_count)
            self.control.seek_slider.setValue(self._playing_seg)

    def _start(self):
        u=self.control.url_input.text().strip()
        if not u:QMessageBox.warning(self,"Error","Enter MPD URL");return
        self._cleanup()
        self._seg_buf=queue.Queue(10);self._frame_buf=queue.Queue(96)
        self._dl_count=0;self._paused=False;self._done=False;self._stopped=False
        self.control.btn_start.setEnabled(False);self.control.btn_start.setText("Working...")
        self.control.set_transport_enabled(True);self.control.set_playing(True)
        self.control.update_stats(status="Buffering...",total_segments=0)
        self._poll.start();self._video.set_status("Buffering...")
        threading.Thread(target=self._download,args=(u,self.control.strategy_combo.currentText()),daemon=True).start()
        threading.Thread(target=self._player,daemon=True).start()

    def _download(self,url,stn):
        try:
            from streaming.parse_mpd import ParseMpd;from streaming.buffer_manager import BufferManager
            from strategy import create_strategy;from utils.logger import initialize_logger
            p=ParseMpd();r=p.parse_mpd(url)
            tot=r['total_seq'];th=r['threshold'];vn=url.split('/')[-1].replace('.mpd','')
            self._w=int(r['width']);self._h=int(r['height']);self._fs=self._w*self._h*3
            fps=float(r.get('frame_rate',24));self._ft.setInterval(int(1000/fps))
            self.control.update_stats(total_segments=tot)
            self.control.seek_slider.setMaximum(tot-1)
            self.control.seek_slider.setEnabled(True)
            self.control.update_stats(status=f"{r['width']}x{r['height']}, {tot} segs")
            if not os.path.exists('log'):os.makedirs('log')
            initialize_logger(os.path.join(os.getcwd(),'log'))
            bu=r['base_url']
            if'192.168'in bu or'concert.itec'in bu:bu='http://127.0.0.1:8087/dataset/I/segs/360p/';r['base_url']=bu
            bf=BufferManager(bu,bu.split('//')[-1].replace('/','.',).replace(': ',','))
            def dl(seg_url):
                fn=os.path.basename(seg_url);t0=time.time()
                req=urllib.request.Request(bf.base_url+seg_url);req.add_header('User-Agent','DASH-Client/3.0')
                with urllib.request.urlopen(req,timeout=30)as resp:data=resp.read()
                with open(fn,'wb')as f:f.write(data);ti=max(time.time()-t0,0.001)
                return fn,float(len(data)*8/ti),ti
            bf.download_wget=dl
            so=create_strategy(stn, quality=0)
            if not os.path.exists(vn):os.makedirs(vn)
            seg_base,speed,_=bf.download_init_segment(vn,r['data'])
            for i in range(self._start_seg, tot):
                if self._stopped:break
                layer=so.select_layer(i,speed,bf.buffer_list.qsize(),th)
                files,speed,tm=bf.download_segment(layer,i,r['list_url'])
                seg_out=f'{vn}/seg_{i}.264'
                bf.generate_h264(vn,i,files,seg_base,seg_out)
                self._seg_buf.put(seg_out)
                so.update_state(bf.buffer_list.qsize(),speed);self._dl_count=i+1
                self.control.update_stats(segment=i+1,speed=speed/1024/8,bandwidth=speed/1024/8)
            if not self._stopped:self._seg_buf.put(None)
            self._dl_finished=True;so.finalize()
        except Exception as e:traceback.print_exc()

    def _player(self):
        first=True
        while not self._stopped:
            seg_path=self._seg_buf.get()
            if seg_path is None:break
            while self._paused and not self._stopped:time.sleep(0.1)
            try:
                proc=subprocess.Popen(['/Users/yrj/bin/ffmpeg','-i',seg_path,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
                self._ffmpeg_procs.append(proc)
                while not self._stopped:
                    while self._paused and not self._stopped:time.sleep(0.1)
                    data=proc.stdout.read(self._fs)
                    if not data or len(data)<self._fs:break
                    self._frame_buf.put(data)
                    if first:first=False;self._msgq.put('start_ft')
                proc.wait()
                self._ffmpeg_procs.remove(proc)
                try:os.unlink(seg_path)
                except:pass
            except:pass
        self._player_done=True
        if not self._stopped:self._frame_buf.put(None)

    def _show_frame(self):
        if self._done or self._stopped:return
        try:
            data=self._frame_buf.get_nowait()
            if data is None:
                self._ft.stop();self._done=True;self._video.set_status("Finished")
                self.control.update_stats(status="Finished");self.control.set_playing(False)
                self.control.set_transport_enabled(False)
                self.control.btn_start.setEnabled(True);self.control.btn_start.setText("Start Streaming")
                return
            img=QImage(data,self._w,self._h,self._w*3,QImage.Format_RGB888)
            self._video.set_frame(img);self._video.set_status("Playing");self._frame_count+=1;self._playing_seg=self._frame_count//48
        except queue.Empty:
            # Only truly finished when player thread has exited AND all buffers are empty
            if self._player_done and self._frame_buf.qsize()==0:
                self._ft.stop();self._done=True;self._video.set_status("Finished")
                self.control.update_stats(status="Finished");self.control.set_playing(False)
                self.control.set_transport_enabled(False)
                self.control.btn_start.setEnabled(True);self.control.btn_start.setText("Start Streaming")

    def _toggle_pause(self):
        self._paused=not self._paused
        self.control.set_playing(not self._paused)
        self._video.set_status("Paused" if self._paused else "Playing")

    def _seek(self):
        """Seek: clear all, restart download from target, buffer 10, then play."""
        target = self.control.seek_slider.value()
        # Kill FFmpeg and player
        self._stopped = True
        for p in self._ffmpeg_procs:
            try:p.kill()
            except:pass
        self._ffmpeg_procs.clear()
        # Clear all buffers
        try:
            while True:self._seg_buf.get_nowait()
        except:pass
        try:
            while True:self._frame_buf.get_nowait()
        except:pass
        # Reset state
        self._seg_buf = queue.Queue(10)
        self._frame_buf = queue.Queue(96)
        self._dl_count = target; self._start_seg = target
        self._frame_count = 0; self._playing_seg = target
        self._dl_finished = False; self._player_done = False
        self._stopped = False; self._paused = False; self._done = False
        self._ft.stop()
        self.control.update_stats(segment=target, buffer_size=0)
        self.control.update_stats(status="Seeking to seg %d..." % target)
        self._video.set_status("Seeking to seg %d..." % target)
        # Restart download from target
        threading.Thread(target=self._download, args=(self.control.url_input.text().strip(), self.control.strategy_combo.currentText()), daemon=True).start()
        threading.Thread(target=self._player, daemon=True).start()

    def _stop(self):
        self._stopped=True;self._paused=True
        # Kill all FFmpeg processes aggressively
        import subprocess as sp
        sp.run(['pkill','-9','-f','ffmpeg.*BBB'],capture_output=True)
        sp.run(['pkill','-9','-f','ffmpeg.*seg_'],capture_output=True)
        # Unblock stuck threads by draining queues
        try:
            while True:self._seg_buf.get_nowait()
        except:pass
        try:
            while True:self._frame_buf.get_nowait()
        except:pass
        self._cleanup()
        self._poll.stop();self._ft.stop();self._done=True
        self.control.btn_start.setEnabled(True);self.control.btn_start.setText("Start Streaming")
        self.control.set_transport_enabled(False);self.control.set_playing(False)
        self._video.set_status("Stopped");self.control.update_stats(status="Stopped")

    def _cleanup(self):
        for p in self._ffmpeg_procs:
            try:p.kill()
            except:pass
        self._ffmpeg_procs.clear()
        import glob,shutil
        for d in glob.glob('BBB-I-360p*'):shutil.rmtree(d,ignore_errors=True)

    def closeEvent(self,e):self._stop();super().closeEvent(e)
