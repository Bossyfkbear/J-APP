"""Offline desktop front-end. Uses standard-library Tk; no network or models."""
import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from .core import analyze, convert, detect_tempo
from .music import detect_key, detect_chords
from .harmony import progression
from .models import denoise, runtime_status, separate_vocals
from .quality import inspect_audio
from .loudness import measure_loudness

OPERATIONS = ('Analyze', 'Quality Check', 'Loudness / True Peak', 'AI Model Status', 'Tempo', 'Key', 'Chords', 'Progression', 'Convert', 'AI Denoise (DeepFilterNet)', 'Vocal Separation (Demucs)')

def run_operation(operation, source, destination='', key='', convert_settings=None):
    if operation == 'AI Model Status':
        return runtime_status(key or None)
    if not Path(source).is_file():
        raise FileNotFoundError(f'Input file not found: {source}')
    if operation == 'Analyze': return analyze(source)
    if operation == 'Quality Check': return inspect_audio(source)
    if operation == 'Loudness / True Peak': return measure_loudness(source)
    if operation == 'Tempo': return detect_tempo(source)
    if operation == 'Key': return detect_key(source)
    if operation == 'Chords': return detect_chords(source)
    if operation == 'Progression': return progression(source, 1.0, key or None)
    if operation == 'AI Denoise (DeepFilterNet)':
        if not destination: raise ValueError('Select a WAV output file')
        return denoise(source, destination, key)
    if operation == 'Vocal Separation (Demucs)':
        if not destination: raise ValueError('Select a vocals WAV output file')
        return separate_vocals(source, destination, key)
    if operation == 'Convert':
        if not destination or Path(source).resolve() == Path(destination).resolve():
            raise ValueError('Choose a different output file to avoid overwriting input')
        if Path(destination).exists():
            raise FileExistsError('Output already exists; choose another filename')
        options = convert_settings or {}
        return {'output': str(convert(source, destination,
                                      options.get('sample_rate'), options.get('channels'),
                                      options.get('codec')))}
    raise ValueError('Unknown operation')

def main():
    root = tk.Tk()
    root.title('Audio Post Toolkit — Offline')
    root.geometry('850x570')
    root.minsize(640, 440)
    frame = ttk.Frame(root, padding=14)
    frame.pack(fill='both', expand=True)
    src = tk.StringVar(); dst = tk.StringVar(); key = tk.StringVar(); operation = tk.StringVar(value='Analyze')
    sample_rate = tk.StringVar(); channels = tk.StringVar(); wav_depth = tk.StringVar(value='Source / default')
    results = queue.Queue()
    def browse_src():
        path = filedialog.askopenfilename(filetypes=[('Audio files', '*.wav *.flac *.aiff *.aif *.ogg *.mp3'), ('All files', '*.*')])
        if path: src.set(path)
    def browse_dst():
        path = filedialog.asksaveasfilename(defaultextension='.wav',filetypes=[('WAV', '*.wav'),('FLAC', '*.flac'),('AIFF','*.aiff')])
        if path: dst.set(path)
    ttk.Label(frame, text='Source audio').grid(row=0,column=0,sticky='w')
    ttk.Entry(frame,textvariable=src).grid(row=1,column=0,sticky='ew',padx=(0,8))
    ttk.Button(frame,text='Browse',command=browse_src).grid(row=1,column=1)
    ttk.Label(frame,text='Module').grid(row=2,column=0,sticky='w',pady=(12,0))
    ttk.Combobox(frame,textvariable=operation,values=OPERATIONS,state='readonly').grid(row=3,column=0,sticky='ew')
    ttk.Label(frame,text='Key override / local AI model directory').grid(row=4,column=0,sticky='w',pady=(12,0))
    ttk.Entry(frame,textvariable=key).grid(row=5,column=0,sticky='ew',padx=(0,8))
    def browse_model():
        path = filedialog.askdirectory(title='Select local DeepFilterNet model directory')
        if path: key.set(path)
    ttk.Button(frame,text='Model folder',command=browse_model).grid(row=5,column=1)
    ttk.Label(frame,text='Output path (Convert / AI Denoise / Vocals WAV)').grid(row=6,column=0,sticky='w',pady=(12,0))
    ttk.Entry(frame,textvariable=dst).grid(row=7,column=0,sticky='ew',padx=(0,8))
    ttk.Button(frame,text='Save as',command=browse_dst).grid(row=7,column=1)
    options = ttk.Frame(frame)
    options.grid(row=8,column=0,columnspan=2,sticky='ew',pady=(12,0))
    ttk.Label(options,text='Convert: Hz').pack(side='left')
    ttk.Entry(options,textvariable=sample_rate,width=9).pack(side='left',padx=(5,14))
    ttk.Label(options,text='Channels').pack(side='left')
    ttk.Entry(options,textvariable=channels,width=5).pack(side='left',padx=(5,14))
    ttk.Label(options,text='WAV depth').pack(side='left')
    ttk.Combobox(options,textvariable=wav_depth,width=18,state='readonly',
                 values=('Source / default','16-bit PCM','24-bit PCM','32-bit PCM','32-bit float')).pack(side='left',padx=(5,0))
    status = tk.StringVar(value='Ready — processing is local and offline')
    output = tk.Text(frame,wrap='word',height=12)
    output.grid(row=10,column=0,columnspan=2,sticky='nsew',pady=(12,0))
    ttk.Label(frame,textvariable=status).grid(row=11,column=0,columnspan=2,sticky='w',pady=(8,0))
    frame.columnconfigure(0,weight=1); frame.rowconfigure(10,weight=1)
    def poll():
        try:
            success, value = results.get_nowait()
        except queue.Empty:
            if root.winfo_exists(): root.after(100,poll)
            return
        run_button.config(state='normal')
        status.set('Complete' if success else 'Error')
        output.delete('1.0','end')
        output.insert('end',json.dumps(value,indent=2,ensure_ascii=False,default=str) if success else str(value))
        if root.winfo_exists(): root.after(100,poll)
    def run():
        run_button.config(state='disabled'); status.set('Processing…')
        op,s,d,k = operation.get(),src.get(),dst.get(),key.get()
        try:
            sr = ch = codec = None
            if op == 'Convert':
                sr = int(sample_rate.get()) if sample_rate.get().strip() else None
                ch = int(channels.get()) if channels.get().strip() else None
                if sr is not None and not 8000 <= sr <= 384000: raise ValueError('Sample rate must be 8000–384000 Hz')
                if ch is not None and not 1 <= ch <= 32: raise ValueError('Channels must be 1–32')
                codec = {'Source / default': None,'16-bit PCM':'pcm_s16le',
                         '24-bit PCM':'pcm_s24le','32-bit PCM':'pcm_s32le',
                         '32-bit float':'pcm_f32le'}[wav_depth.get()]
                if codec and Path(d).suffix.lower() != '.wav':
                    raise ValueError('WAV depth selection requires .wav output')
        except (ValueError,KeyError) as exc:
            run_button.config(state='normal'); status.set(f'Error: {exc}')
            return
        def work():
            try: results.put((True,run_operation(op,s,d,k,{'sample_rate':sr,'channels':ch,'codec':codec})))
            except Exception as exc: results.put((False,f'{type(exc).__name__}: {exc}'))
        threading.Thread(target=work,daemon=True).start()
    run_button = ttk.Button(frame,text='Run offline analysis',command=run)
    run_button.grid(row=9,column=0,sticky='w',pady=(12,0))
    root.after(100,poll)
    root.mainloop()

if __name__ == '__main__': main()
