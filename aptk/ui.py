"""Lightweight professional desktop UI. Tkinter is in Python stdlib."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    BASE_TK = TkinterDnD.Tk
except ImportError:
    DND_FILES = None
    BASE_TK = tk.Tk

from . import __version__
from . import core

BG = "#111721"
NAV = "#161D28"
SURFACE = "#1C2533"
SURFACE_2 = "#232E3E"
FG = "#EEF3F7"
SECONDARY = "#93A5B5"
ACCENT = "#63D9E5"
GOOD = "#9DE2B9"
WARNING = "#F3BE79"
BORDER = "#354251"
FONT = "Microsoft JhengHei UI" if os.name == "nt" else "DejaVu Sans"

# Every tool is an independent operation. None needs other tools to be run first.
TOOLS = [
    ("轉換與交件", [
        ("setup", "環境檢查", "檢查本機 FFmpeg、套件與播放設備", "核心功能"),
        ("convert", "音訊轉檔", "無損優先｜批次格式與規格轉換", "核心功能"),
        ("loudscan", "響度分析", "Integrated LUFS · True Peak · LRA", "核心功能"),
        ("normalize", "響度統一", "EBU R128 響度雙階段處理", "核心功能"),
        ("inspect", "音檔規格檢視", "取樣率、聲道、編碼、位元深度與長度", "核心功能"),
        ("quality", "品質檢測", "Peak · RMS · DC Offset · 異常值", "核心功能"),
        ("silence", "靜音偵測", "分析音訊靜音區段與時間", "核心功能"),
    ]),
    ("修復", [
        ("dereverb", "去混響 WPE", "降低晚期殘響；非神經模型", "選裝修復"),
        ("residual", "底噪提取", "原音訊減去降噪結果，提取殘差", "核心功能"),
        ("declick", "去雜音", "修復 Click / Pop 類型瞬態雜音", "核心功能"),
        ("declip", "去爆音", "還原部分過載削波片段", "核心功能"),
        ("deess", "去齒音", "處理人聲齒音與高頻尖刺", "核心功能"),
    ]),
    ("音樂與 AI", [
        ("ai_denoise", "AI 人聲降噪", "DeepFilterNet 本機神經模型（選裝）", "選裝模型"),
        ("split", "人聲／樂器分離", "Demucs AI：人聲、伴奏或四軌", "選裝模型"),
        ("rhythm", "BPM／調性", "節拍速度與音樂調性估計", "選裝分析"),
        ("pitch", "音高追蹤", "單音 pYIN · 音名 · 音分", "選裝分析"),
        ("meter", "AI 拍點／小節分析", "Beat This! 拍點與小節起點", "選裝模型"),
        ("chords", "和弦分析", "時間軸和弦估計", "實驗功能"),
        ("progression", "和弦進行", "和弦與羅馬數字估計", "實驗功能"),
        ("ai_status", "AI 模型狀態", "檢查本機模型能否載入", "選裝模型"),
    ]),
    ("音色與檔案", [
        ("mic", "麥克風音色", "可用參考錄音做頻譜匹配 EQ，或使用原 U87 風格草案", "實驗功能"),
        ("rename", "批次重新命名", "複製並命名，不動原檔", "核心功能"),
        ("compare", "音檔比對", "檢查波形相關性與差異 RMS", "選裝分析"),
        ("verify", "完整精度比對", "全檔逐聲道比對，不降採樣", "核心功能"),
        ("align", "時間對齊分析", "估算兩個音檔的時間偏移（不改原檔）", "選裝分析"),
    ]),
]
TOOL_INFO = {k:(title,desc,tag) for _, sect in TOOLS for k,title,desc,tag in sect}
TOOL_CATEGORY = {k:group for group,entries in TOOLS for k,_,_,_ in entries}
CATEGORY_TOOLS = {group:tuple(k for k,_,_,_ in entries) for group,entries in TOOLS}

OPTIONS = {
    "meter": [("model_dir","Beat This! 模型資料夾", "folder", [], ""),
              ("runtime_python","分析環境 Python（留空自動選取）", "file", [], "")],
    "pitch": [("runtime_python","分析環境 Python（留空自動選取）", "file", [], "")],
    "dereverb": [("strength","處理比例（0–1）", "select", ["0.25","0.5","0.75","1.0"], "0.5"),
                 ("runtime_python","處理環境 Python（留空自動選取）", "file", [], "")],
    "convert": [("fmt","輸出格式", "select", ["wav","flac","aiff","mp3","aac"], "wav"),
                ("depth","位元深度", "select", ["auto","16","24","32","32f","64f"], "auto"),
                ("rate","取樣率 Hz", "select", ["保留","44100","48000","88200","96000","192000"], "保留"),
                ("channels","聲道", "select", ["保留","1","2"], "保留")],
    "denoise": [("noise_amount","FFT 降噪量 (dB)", "select", ["6","9","12","18","24","30"], "12"),
                ("depth","輸出精度", "select", ["24","32f"], "24")],
    "residual": [("noise_amount","殘差提取強度 (dB)", "select", ["6","12","18","24"], "12")],
    "declick": [("depth","輸出精度", "select", ["24","32f"], "24")],
    "declip": [("depth","輸出精度", "select", ["24","32f"], "24")],
    "deess": [("depth","輸出精度", "select", ["24","32f"], "24")],
    "normalize": [("target_i","目標 LUFS", "select", ["-24","-23","-20","-18","-16","-14"], "-16"),
                  ("target_tp","True Peak 上限 dBTP", "select", ["-3","-2","-1.5","-1"], "-1.5"),
                  ("target_lra","目標 LRA", "select", ["7","11","15"], "11"),
                  ("depth","輸出位元深度", "select", ["auto","16","24","32f","64f"], "auto")],
    "silence": [("silence_db","閾值 dBFS", "select", ["-60","-50","-45","-40","-35"], "-45"),
                 ("silence_sec","最短靜音 (秒)", "select", ["0.2","0.35","0.5","1.0","2.0"], "0.35")],
    "ai_status": [("model_dir","本機 DeepFilterNet 模型資料夾", "folder", [], ""),
                  ("runtime_python","AI Python（留空自動選取）", "file", [], "")],
    "ai_denoise": [("model_dir","本機 DeepFilterNet 模型資料夾", "folder", [], ""),
                   ("runtime_python","AI Python（留空自動選取）", "file", [], "")],
    "split": [("split_mode","分離模式", "select", ["vocal","four"], "vocal"),
              ("model_dir","本機 Demucs 模型資料夾", "folder", [], ""),
              ("model_name","模型名稱（單一模型可留空）", "text", [], ""),
              ("runtime_python","AI Python（留空自動選取）", "file", [], "")],
    "mic": [("mic_strength","音色匹配／EQ 強度 (%)", "select", ["0","25","50","65","80","100"], "65"),
            ("reference_path","目標麥克風參考錄音 (可選)", "file", [], ""),
            ("depth","未選參考檔時 EQ 輸出精度", "select", ["24","32f"], "24")],
    "rename": [("prefix","檔名開頭", "text", [], "Audio_"),
               ("number_start","起始編號", "text", [], "1"),
               ("padding","編號位數", "select", ["3","4","5","6"], "4")],
}

EXTRA = {
    "setup": "不需要音檔：檢查 FFmpeg、音效設備與五個選裝 AI 模組。可安裝所選 AI 模組，完成後自動使用已安裝的模型路徑；安裝需明確確認。可播放低音量測試音。缺少 FFmpeg 可執行 setup_ffmpeg_windows.bat。",
    "meter": "使用官方 Beat This! 預訓練模型分析前 3 分鐘的拍點、小節起點與每小節偵測拍數。使用本機模型，不上傳音檔。樂譜拍號仍需人工確認。",
    "pitch": "pYIN 追蹤單人聲或單樂器的基頻、音名及音分，非多聲部扒譜。範圍 50–1200 Hz，最多分析前 10 分鐘；可能有八度誤判。",
    "verify": "比對兩檔的全部解碼樣本，保留原取樣率及各聲道。取樣率或聲道不同會列出差異，不產生誤導性的相減結果。不是聽感評分。",
    "dereverb": "WPE 線性預測降低晚期殘響，非 AI。保留取樣率、聲道及長度，輸出 32-bit float WAV；空間感與音色可能改變，請預聽。需選裝 nara-wpe / scipy。",
    "convert": "保留取樣率與聲道為預設；WAV 24-bit 會重新量化，並非位元完全複製。MP3／AAC 是有損編碼，只有明確選用才會使用。",
    "denoise": "使用 FFmpeg afftdn 的 FFT 頻譜降噪，無需模型。較強降噪可能損傷語音的細節與空間感。",
    "residual": "這是「原聲 − 降噪後」的近似殘差，不等於真正獨立的環境底噪。可能含語音殘影。",
    "declick": "適用短暫點狀 Click/Pop，非所有碰撞或口水聲都能完全修復。",
    "declip": "對已被截斷的波形做估測重建，無法復原不存在的原始資訊。",
    "deess": "目前使用保守的固定參數。後續可增加頻帶選擇與預聽調整。",
    "loudscan": "輸出 UTF-8 文字報告，不修改原始音訊。",
    "normalize": "雙階段 EBU R128。輸出 WAV 24-bit，保留來源取樣率及聲道；此工具會刻意調整電平。",
    "inspect": "只讀取檔案資訊，不解碼、不重新取樣、不改變任何聲音。",
    "quality": "只進行測量，不修改原始音訊。品質指標不能取代實際聽音。",
    "silence": "只標記靜音區段，不切檔，也不刪除任何音訊。",
    "ai_denoise": "需本機 DeepFilterNet 模型與相容環境。內部使用 48 kHz，輸出還原來源取樣率、聲道及已知 PCM 精度；有損來源輸出 24-bit WAV。不會恢復模型頻寬外的細節。",
    "split": "需另外安裝 Demucs 並選取本機模型資料夾。模式 vocal：人聲與伴奏；four：人聲、鼓、貝斯、其他。",
    "rhythm": "按「開始處理」後，分析完成即彈出 BPM、拍號、調性。只顯示結果，不輸出 JSON 或計算過程。",
    "mic": "提供同聲源、同環境、相同取樣率的目標麥克風 WAV/FLAC/AIFF，進行保守 EQ 匹配（最多 ±6 dB，輸出 32f WAV）；不會模擬 U87 的指向性、瞬態或電子特性。不選參考檔則保留原本的 U87 風格 EQ 草案。",
    "rename": "安全複製新檔名，不搬動或覆蓋原始音檔。",
    "chords": "和弦估計可能受複雜混音影響。",
    "progression": "羅馬數字依估計調性解讀，需人工核對。",
    "ai_status": "嘗試載入指定本機模型，不下載模型。",
    "compare": "需選裝 numpy。比較前兩個檔案最長 120 秒，不自動對齊，因此要先同步時間與相位。",
    "align": "需選裝 numpy。分析前 45 秒的音量包絡，估計 ±20 秒偏移；不修改音檔，請人工核對。",
}

def selected_preview_path(files: list[Path], selection, output_pairs: dict, *, processed: bool = False) -> Path | None:
    """Resolve preview by selected source, never by an unrelated last batch output."""
    if not files:
        return None
    index = selection[0] if selection and 0 <= selection[0] < len(files) else 0
    source = Path(files[index])
    if not processed:
        return source
    value = output_pairs.get(str(source.resolve()))
    return Path(value) if value else None


class App(BASE_TK):
    def __init__(self):
        super().__init__()
        self.title("Audio Post Toolkit — v" + __version__)
        self.geometry("1160x760")
        self.minsize(970, 640)
        self.configure(bg=BG)
        self.tool = "convert"
        self.category = TOOL_CATEGORY[self.tool]
        self.category_last_tool = {}
        self.files: list[Path] = []
        self.option_vars: dict[str,tk.StringVar] = {}
        self.saved_options = {}
        self.destination = tk.StringVar(value="")
        self.output_file: Path | None = None
        self.is_running = False
        self.playback_in_progress = False
        self.playback_confirmed_in_session = False
        self.qa_running = False
        self.ai_verify_running = False
        self.ai_verify_process = None
        self.ai_install_running = False
        self.ai_install_process = None
        self.ai_test_module = tk.StringVar(value='denoise')
        self.events: queue.Queue = queue.Queue()
        self.preview_process = None
        self.ab_player = None
        self.ab_request = 0
        self.output_pairs = {}
        self.ab_start = tk.StringVar(value='0')
        self.ab_seconds = tk.StringVar(value='30')
        self.ab_offset = tk.StringVar(value='0')
        self.ab_match = tk.BooleanVar(value=False)
        self.waveform = []
        self.waveform_seconds = 0.0
        self.waveform_start = 0.0
        self.waveform_span = 120.0
        self.waveform_total = 0.0
        self.waveform_cursor = None
        self.waveform_request = 0
        self.waveform_reload_after = None
        self.waveform_redraw_after = None
        self.waveform_seek_updating = False
        self._init_styles()
        self._build()
        self.after(100, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind_all("<Control-o>", lambda e: self.add_files())
        self.bind_all("<Escape>", lambda e: self.stop_preview())

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.TCombobox", foreground=FG, fieldbackground=SURFACE_2, background=SURFACE_2, arrowcolor=ACCENT, bordercolor=BORDER, selectbackground=SURFACE_2, selectforeground=FG, padding=(9,7))
        style.map("Dark.TCombobox", fieldbackground=[("readonly", SURFACE_2)], foreground=[("readonly", FG)])
        self.option_add("*TCombobox*Listbox.background", SURFACE_2)
        self.option_add("*TCombobox*Listbox.foreground", FG)

    def text(self, parent, value, *, size=11, color=FG, bold=False, bg=None, **kwargs):
        return tk.Label(parent, text=value, font=(FONT,size,"bold" if bold else "normal"), bg=bg or parent.cget("bg"), fg=color, **kwargs)

    def button(self, parent, value, command, *, accent=False, width=None):
        return tk.Button(parent,text=value,command=command,bg=ACCENT if accent else SURFACE_2, fg="#0A1A22" if accent else FG,
                         activebackground="#8BEAF2" if accent else "#354557",activeforeground="#09161C" if accent else FG,
                         font=(FONT,10,"bold"),relief="flat", bd=0, padx=14,pady=9,cursor="hand2",width=width, highlightthickness=0)

    def _build(self):
        header = tk.Frame(self,bg=NAV,height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Canvas(header,width=27,height=27,bg=NAV,highlightthickness=0).pack(side="left",padx=(24,10))
        # Waveform symbol (drawn, no image dependencies).
        canv = header.winfo_children()[0]
        for x,h in [(4,8),(9,17),(14,25),(19,16),(24,9)]:
            canv.create_line(x,(27-h)/2,x,(27+h)/2,fill=ACCENT,width=2.8,capstyle="round")
        self.text(header,"AUDIO POST",size=13,bold=True,bg=NAV).pack(side="left")
        self.text(header,"TOOLKIT",size=13,bold=True,bg=NAV,color=ACCENT).pack(side="left",padx=(5,0))
        self.text(header,"OFFLINE  /  MODULAR  /  LOSSLESS-FIRST",size=9,bg=NAV,color=SECONDARY).pack(side="right",padx=25)

        root = tk.Frame(self,bg=BG)
        root.pack(fill="both",expand=True)
        self.sidebar = tk.Frame(root,bg=NAV,width=252)
        self.sidebar.pack(side="left",fill="y")
        self.sidebar.pack_propagate(False)
        sidebar_outer=tk.Frame(self.sidebar,bg=NAV)
        sidebar_outer.pack(fill="both",expand=True)
        navc=tk.Canvas(sidebar_outer,bg=NAV,highlightthickness=0,width=246)
        scrollbar=ttk.Scrollbar(sidebar_outer,orient="vertical",command=navc.yview)
        navc.configure(yscrollcommand=scrollbar.set)
        navc.pack(side="left",fill="both",expand=True)
        scrollbar.pack(side="right",fill="y")
        self.navscroll=navc
        navinner=tk.Frame(navc,bg=NAV)
        navc.create_window((0,0),window=navinner,anchor="nw")
        navinner.bind("<Configure>",lambda e:navc.configure(scrollregion=navc.bbox("all")))
        self.navbuttons={}
        # Top-level sidebar contains ONLY major groups. Individual tools live
        # together in the main category workspace, without 25 nav entries.
        self.text(navinner,"功能分類",size=10,color=SECONDARY,bg=NAV).pack(anchor="w",padx=24,pady=(20,8))
        for group,entries in TOOLS:
            btn=tk.Button(navinner,text=f"  {group}   ({len(entries)})",anchor="w",
                          command=lambda cat=group:self.select_category(cat),
                          font=(FONT,11,"bold"),relief="flat",bd=0,bg=NAV,fg="#B7C5D0",
                          activebackground=SURFACE_2,activeforeground=ACCENT,
                          padx=18,pady=13,width=22,cursor="hand2",highlightthickness=0)
            btn.pack(fill="x",padx=(8,8),pady=(1,5))
            self.navbuttons[group]=btn
        self.text(self.sidebar,"v"+__version__+"  ·  輕量開發版",size=9,color=SECONDARY,bg=NAV).pack(side="bottom",anchor="w",padx=24,pady=17)
        self.content=tk.Frame(root,bg=BG)
        self.content.pack(side="left",fill="both",expand=True,padx=27,pady=23)
        self._build_content()
        self.select_category("轉換與交件")

    def _build_content(self):
        title_row=tk.Frame(self.content,bg=BG)
        title_row.pack(fill="x")
        self.title_label=self.text(title_row,"",size=23,bold=True)
        self.title_label.pack(side="left")
        self.tag_label=self.text(title_row,"",size=9,color=ACCENT)
        self.tag_label.pack(side="right")
        self.subtitle=self.text(self.content,"",size=11,color=SECONDARY,anchor="w")
        self.subtitle.pack(fill="x",pady=(8,14))
        editor_outer=tk.Frame(self.content,bg=BG)
        editor_outer.pack(fill="both",expand=True)
        self.editor_canvas=tk.Canvas(editor_outer,bg=BG,highlightthickness=0,bd=0)
        editor_sb=ttk.Scrollbar(editor_outer,orient="vertical",command=self.editor_canvas.yview)
        self.editor_canvas.configure(yscrollcommand=editor_sb.set)
        self.editor_canvas.pack(side="left",fill="both",expand=True)
        editor_sb.pack(side="right",fill="y")
        self.editor=tk.Frame(self.editor_canvas,bg=BG)
        self.editor_window=self.editor_canvas.create_window((0,0),window=self.editor,anchor="nw")
        self.editor.bind("<Configure>",lambda e:self.editor_canvas.configure(scrollregion=self.editor_canvas.bbox("all")))
        self.editor_canvas.bind("<Configure>",lambda e:self.editor_canvas.itemconfigure(self.editor_window,width=e.width))
        self.editor_canvas.bind("<Enter>",lambda e:self.editor_canvas.bind_all("<MouseWheel>",self._wheel))
        self.editor_canvas.bind("<Leave>",lambda e:self.editor_canvas.unbind_all("<MouseWheel>"))

        self.group_card=tk.Frame(self.editor,bg=SURFACE,highlightbackground=BORDER,highlightthickness=1)
        self.group_card.pack(fill="x",pady=(0,13))
        group_header=tk.Frame(self.group_card,bg=SURFACE)
        group_header.pack(fill="x",padx=16,pady=(12,3))
        self.text(group_header,"分類功能",size=10,bold=True,bg=SURFACE).pack(side="left")
        self.category_count=self.text(group_header,"",size=9,color=SECONDARY,bg=SURFACE)
        self.category_count.pack(side="right")
        self.group_tools=tk.Frame(self.group_card,bg=SURFACE)
        self.group_tools.pack(fill="x",padx=12,pady=(4,12))
        for i in range(3):
            self.group_tools.columnconfigure(i,weight=1,uniform="category_tools")
        self.toolbuttons={}

        self.file_card=tk.Frame(self.editor,bg=SURFACE,highlightbackground=BORDER,highlightthickness=1)
        self.file_card.pack(fill="x",pady=(0,13))
        file_toolbar=tk.Frame(self.file_card,bg=SURFACE)
        file_toolbar.pack(fill="x",padx=16,pady=(13,9))
        self.text(file_toolbar,"SOURCE FILES",size=10,bold=True,bg=SURFACE).pack(side="left")
        self.button(file_toolbar,"＋ 新增音檔",self.add_files).pack(side="right",padx=(8,0))
        self.button(file_toolbar,"清空",self.clear_files).pack(side="right")
        self.file_list=tk.Listbox(self.file_card,height=2,bg=SURFACE,fg=FG,selectbackground="#2A5963",selectforeground=FG,
                                  relief="flat",highlightthickness=0,bd=0,activestyle="none",font=(FONT,10),exportselection=False)
        self.file_list.pack(fill="x",padx=18)
        self.file_list.bind("<<ListboxSelect>>",self._selection_changed)
        if DND_FILES is not None:
            self.file_list.drop_target_register(DND_FILES)
            self.file_list.dnd_bind("<<Drop>>",self._handle_drop)
        bottom=tk.Frame(self.file_card,bg=SURFACE)
        bottom.pack(fill="x",padx=16,pady=(6,14))
        self.filecount=self.text(bottom,"尚未加入音檔",size=9,color=SECONDARY,bg=SURFACE)
        self.filecount.pack(side="left")
        self.button(bottom,"移除選取",self.remove_selected).pack(side="right")

        wavecard=tk.Frame(self.editor,bg=SURFACE,highlightbackground=BORDER,highlightthickness=1)
        wavecard.pack(fill="x",pady=(0,13))
        top=tk.Frame(wavecard,bg=SURFACE)
        top.pack(fill="x",padx=16,pady=(10,0))
        self.text(top,"WAVEFORM PREVIEW",size=9,bold=True,bg=SURFACE,color=SECONDARY).pack(side="left")
        self.waveinfo=self.text(top,"波形預覽",size=9,bg=SURFACE,color=SECONDARY)
        self.waveinfo.pack(side="right")
        wave_controls=tk.Frame(wavecard,bg=SURFACE)
        wave_controls.pack(fill="x",padx=16,pady=(0,5))
        self.text(wave_controls,"點波形設定預聽起點",size=9,bg=SURFACE,color=SECONDARY).pack(side="left")
        for caption,action in (
            ("←",lambda:self.pan_wave(-1)),
            ("→",lambda:self.pan_wave(1)),
            ("−",lambda:self.zoom_wave(.5)),
            ("＋",lambda:self.zoom_wave(2)),
            ("120秒",self.reset_wave_zoom),
        ):
            self.button(wave_controls,caption,action).pack(side="right",padx=(5,0))
        self.wavecanvas=tk.Canvas(wavecard,bg=SURFACE,height=120,
                                  highlightthickness=0,cursor="crosshair")
        self.wavecanvas.pack(fill="x",padx=15,pady=(2,3))
        self.wavecanvas.bind("<Configure>",self._schedule_wave_redraw)
        self.wavecanvas.bind("<Button-1>",self._wave_click)
        self.wavecanvas.bind("<MouseWheel>",self._wave_wheel)
        self.wavecanvas.bind("<Button-4>",lambda e:self.zoom_wave(2,e.x))
        self.wavecanvas.bind("<Button-5>",lambda e:self.zoom_wave(.5,e.x))
        self.wave_seek=tk.Scale(wavecard,from_=0,to=100,orient="horizontal",
                                resolution=.1,showvalue=False,length=400,sliderlength=16,
                                width=9,bd=0,highlightthickness=0,
                                bg=SURFACE,fg=FG,troughcolor="#273846",
                                activebackground=ACCENT,command=self._wave_seek_changed)
        self.wave_seek.pack(fill="x",padx=16,pady=(0,8))
        self.wave_seek.config(state="disabled")
        pre=tk.Frame(wavecard,bg=SURFACE)
        pre.pack(fill="x",padx=16,pady=(0,11))
        self.button(pre,"▶ 原音預聽",lambda:self.play_audio(False)).pack(side="left")
        self.button(pre,"▶ 輸出預聽",lambda:self.play_audio(True)).pack(side="left",padx=(8,0))
        self.button(pre,"■ 停止",self.stop_preview).pack(side="left",padx=(8,0))
        ab=tk.Frame(wavecard,bg=SURFACE)
        ab.pack(fill='x',padx=16,pady=(0,11))
        self.button(ab,'▶ 同步 A/B',self.start_ab).pack(side='left')
        self.button(ab,'A 原音',lambda:self.select_ab(0)).pack(side='left',padx=4)
        self.button(ab,'B 輸出',lambda:self.select_ab(1)).pack(side='left')
        self.text(ab,'起點／秒數',size=9,bg=SURFACE).pack(side='left',padx=8)
        tk.Entry(ab,textvariable=self.ab_start,width=6).pack(side='left')
        tk.Entry(ab,textvariable=self.ab_seconds,width=6).pack(side='left',padx=4)
        adjust=tk.Frame(wavecard,bg=SURFACE)
        adjust.pack(fill='x',padx=16,pady=(0,11))
        self.text(adjust,'B 延遲補償 ms（正值跳過 B 開頭）',size=9,bg=SURFACE).pack(side='left')
        tk.Entry(adjust,textvariable=self.ab_offset,width=7).pack(side='left',padx=6)
        tk.Checkbutton(adjust,text='預聽響度匹配',variable=self.ab_match,bg=SURFACE,fg=FG,selectcolor=SURFACE_2,activebackground=SURFACE).pack(side='left')
        qc=tk.Frame(wavecard,bg=SURFACE)
        qc.pack(fill='x',padx=16,pady=(0,11))
        self.button(qc,'檢查原音／輸出',self.start_technical_qa).pack(side='left')
        self.text(qc,'只檢查技術規格；仍需實際聽感驗收',size=9,bg=SURFACE,color=SECONDARY).pack(side='left',padx=10)

        control=tk.Frame(self.editor,bg=BG)
        control.pack(fill="x",pady=(0,10))
        self.fields_label=self.text(control,"參數設定",size=12,bold=True)
        self.fields_label.pack(anchor="w",pady=(0,9))
        self.fields=tk.Frame(control,bg=BG)
        self.fields.pack(fill="x")
        folderrow=tk.Frame(control,bg=BG)
        folderrow.pack(fill="x",pady=(12,0))
        self.text(folderrow,"輸出資料夾",size=10,color=SECONDARY).pack(side="left")
        self.folderentry=tk.Entry(folderrow,textvariable=self.destination,bg=SURFACE_2,fg=FG,insertbackground=FG,relief="flat",font=(FONT,10),bd=0)
        self.folderentry.pack(side="left",fill="x",expand=True,padx=(12,8),ipady=8)
        self.button(folderrow,"選擇",self.pick_folder).pack(side="right")
        self.text(control,"留空：自動儲存到原音檔所在資料夾的 APTK_Output，絕不覆蓋原檔。",size=9,color=SECONDARY).pack(anchor="w",pady=(6,0))
        self.helper=self.text(control,"",size=9,color=WARNING,anchor="w",justify="left",wraplength=750)
        self.helper.pack(fill="x",pady=(11,0))

        action=tk.Frame(self.content,bg=BG)
        action.pack(side="bottom",fill="x",pady=(8,5))
        self.runbtn=self.button(action,"開始處理",self.start,accent=True,width=14)
        self.runbtn.pack(side="left")
        self.stopbtn=self.button(action,"取消工作",self.cancel_work)
        self.stopbtn.pack(side="left",padx=(10,0))
        self.state_label=self.text(action,"就緒",size=10,color=SECONDARY)
        self.state_label.pack(side="right")
        self.logframe=tk.Frame(self.content,bg=SURFACE,highlightthickness=1,highlightbackground=BORDER)
        self.logframe.pack(side="bottom",fill="x",pady=(2,0))
        self.logframe.configure(height=122)
        self.logframe.pack_propagate(False)
        bar=tk.Frame(self.logframe,bg=SURFACE)
        bar.pack(fill="x",padx=16,pady=(11,6))
        self.text(bar,"PROCESS LOG",size=9,color=SECONDARY,bold=True,bg=SURFACE).pack(side="left")
        self.logbox=tk.Text(self.logframe,bg=SURFACE,fg="#BCD0D8",insertbackground=ACCENT,font=(FONT,9),relief="flat",bd=0,
                            highlightthickness=0,wrap="word",height=6,state="disabled",takefocus=0)
        self.logbox.pack(fill="both",expand=True,padx=14,pady=(0,12))
        # Keep diagnostics internally for troubleshooting; the normal GUI
        # displays final results only, not command output or raw JSON.
        self.logframe.pack_forget()
        self._draw_wave()

    def _wheel(self,event):
        self.editor_canvas.yview_scroll(-int(event.delta/120),"units")

    def select_category(self, category: str):
        """Open one combined workspace for a major category."""
        if self.is_running or category not in CATEGORY_TOOLS:
            return
        tool = self.tool if TOOL_CATEGORY[self.tool] == category else (
            self.category_last_tool.get(category) or CATEGORY_TOOLS[category][0])
        self.select_tool(tool)

    def select_tool(self, tool: str):
        if self.is_running or tool not in TOOL_INFO:
            return
        self.saved_options[self.tool] = {key: var.get() for key, var in self.option_vars.items()}
        self.tool=tool
        self.category=TOOL_CATEGORY[tool]
        self.category_last_tool[self.category]=tool
        title, desc, tag=TOOL_INFO[tool]
        self.title_label.config(text=self.category)
        self.subtitle.config(text=f"{title}｜{desc}")
        self.tag_label.config(text=tag)
        self.helper.config(text=EXTRA.get(tool,""))
        for group,btn in self.navbuttons.items():
            active = group == self.category
            btn.config(bg="#243C48" if active else NAV,
                       fg=ACCENT if active else "#B7C5D0")
        # All tools in this category appear within ONE panel. Switching
        # tools keeps the source file list, output folder and saved parameters.
        for child in self.group_tools.winfo_children():
            child.destroy()
        self.toolbuttons={}
        members=CATEGORY_TOOLS[self.category]
        self.category_count.config(text=f"{len(members)} 項功能")
        for i,key in enumerate(members):
            name=TOOL_INFO[key][0]
            active=key==tool
            button=tk.Button(self.group_tools,text=name,command=lambda t=key:self.select_tool(t),
                             font=(FONT,10,"bold" if active else "normal"),
                             bg=ACCENT if active else SURFACE_2,
                             fg="#0A1A22" if active else FG,
                             activebackground="#8BEAF2" if active else "#354557",
                             activeforeground="#0A1A22" if active else FG,
                             relief="flat",bd=0,padx=8,pady=11,cursor="hand2",highlightthickness=0)
            button.grid(row=i//3,column=i%3,sticky="ew",padx=4,pady=4)
            self.toolbuttons[key]=button
        for widget in self.fields.winfo_children():
            widget.destroy()
        self.option_vars={}
        rows=OPTIONS.get(tool,[])
        for idx,(key, label, kind, values, default) in enumerate(rows):
            if key == 'model_dir':
                from apt.worker import app_directory
                installed = app_directory() / 'models' / ('BeatThis' if tool=='meter' else 'Demucs' if tool=='split' else 'DeepFilterNet3')
                if installed.is_dir():
                    default = str(installed)
            slot=tk.Frame(self.fields,bg=BG)
            slot.grid(row=idx//2,column=idx%2,sticky="ew",padx=(0,13),pady=(0,9))
            self.text(slot,label,size=9,color=SECONDARY).pack(anchor="w",pady=(0,5))
            val=tk.StringVar(value=self.saved_options.get(tool, {}).get(key, default))
            self.option_vars[key]=val
            if kind=="select":
                control=ttk.Combobox(slot,textvariable=val,values=values,state="readonly",style="Dark.TCombobox")
                control.pack(fill="x")
            elif kind in ("folder", "file"):
                tk.Entry(slot,textvariable=val,bg=SURFACE_2,fg=FG,insertbackground=FG).pack(fill="x")
                def choose_path(v=val, k=kind, option_key=key):
                    if k == 'folder':
                        path = filedialog.askdirectory(title="選擇本機模型資料夾")
                    elif option_key == 'reference_path':
                        path = filedialog.askopenfilename(title="選擇目標麥克風參考錄音",
                            filetypes=[("無損音檔", "*.wav *.wave *.flac *.aif *.aiff"), ("所有檔案", "*.*")])
                    else:
                        path = filedialog.askopenfilename(title="選擇 AI 環境的 Python 執行檔")
                    if path: v.set(path)
                text = "選擇資料夾" if kind=='folder' else "選擇參考音檔" if key=='reference_path' else "選擇 Python"
                self.button(slot,text,choose_path).pack(anchor="w")
            else:
                tk.Entry(slot,textvariable=val,bg=SURFACE_2,fg=FG,insertbackground=FG,relief="flat",font=(FONT,11)).pack(fill="x",ipady=8)
        self.fields.columnconfigure(0,weight=1)
        self.fields.columnconfigure(1,weight=1)
        if tool == 'setup':
            slot = tk.Frame(self.fields, bg=BG)
            slot.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0,10))
            self.text(slot, '實機聲音輸出（需自行確認有聽到）', size=10, color=SECONDARY).pack(anchor='w', pady=(0,5))
            self.button(slot, '▶ 播放 1 秒低音量測試音', self.test_output_device).pack(anchor='w')
            self.button(slot, '安裝／修復 FFmpeg（Windows）', self.install_ffmpeg_windows).pack(anchor='w',pady=(6,0))
            ai = tk.Frame(self.fields, bg=BG)
            ai.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(8,10))
            self.text(ai,'已安裝 AI 模組：本機實際運算自測（不使用私人錄音）',
                      size=10,color=SECONDARY).pack(anchor='w',pady=(0,6))
            ttk.Combobox(ai,textvariable=self.ai_test_module,
                         values=['denoise','split','meter','pitch','dereverb'],
                         state='readonly',style='Dark.TCombobox',width=18).pack(side='left')
            self.button(ai,'安裝所選 AI 模組',self.install_selected_ai).pack(side='left',padx=(0,10))
            self.button(ai,'執行所選模型推論自測',self.test_installed_ai).pack(side='left')
        if tool in ("setup","loudscan","quality","inspect","rhythm","compare","align","silence","verify","pitch"):
            self.fields_label.config(text="分析設定" if rows else "分析工具（不修改原檔）")
        else:
            self.fields_label.config(text="參數設定" if rows else "使用預設專業參數")
        if tool in ('ai_denoise', 'split', 'ai_status', 'dereverb', 'pitch', 'meter'):
            self.state_label.config(text="執行時檢查 AI 環境與模型",fg=SECONDARY)
        elif tool=="rhythm" and importlib.util.find_spec("numpy") is None:
            self.state_label.config(text="NumPy 尚未安裝",fg=WARNING)
        elif tool in ("compare","align") and importlib.util.find_spec("numpy") is None:
            self.state_label.config(text="numpy 尚未安裝",fg=WARNING)
        else:
            self.state_label.config(text="就緒",fg=SECONDARY)

    def _add_paths(self,paths):
        current=set(self.files)
        for path in paths:
            p=Path(path)
            if p.is_file() and p.suffix.lower() in core.AUDIO_TYPES and p not in current:
                self.files.append(p)
                current.add(p)
        self.update_file_list()

    def _handle_drop(self,event):
        self._add_paths(self.tk.splitlist(event.data))

    def add_files(self):
        paths=filedialog.askopenfilenames(title="選擇音檔",filetypes=[("音訊檔案","*.wav *.wave *.aif *.aiff *.flac *.mp3 *.m4a *.aac *.ogg *.opus *.wma *.caf"),("所有檔案","*.*")])
        self._add_paths(paths)

    def update_file_list(self):
        self.file_list.delete(0,"end")
        for p in self.files:
            self.file_list.insert("end",p.name)
        self.filecount.config(text=f"{len(self.files)} 個音檔" if self.files else "尚未加入音檔")
        if self.files:
            self.file_list.select_set(0)
            self.load_waveform(self.files[0])
        else:
            self.waveform_request += 1
            if self.waveform_reload_after is not None:
                self.after_cancel(self.waveform_reload_after)
                self.waveform_reload_after = None
            self.waveform = []
            self.waveform_seconds = 0.
            self.waveform_total = 0.
            self.waveform_cursor = None
            self._update_wave_seek()
            self._draw_wave()

    def remove_selected(self):
        if self.is_running:
            return
        selected=set(self.file_list.curselection())
        self.files=[v for i,v in enumerate(self.files) if i not in selected]
        self.update_file_list()

    def clear_files(self):
        if self.is_running:
            return
        self.files=[]
        self.update_file_list()

    def _selection_changed(self,e=None):
        ix=self.file_list.curselection()
        if ix and ix[0]<len(self.files):
            self.load_waveform(self.files[ix[0]])

    def load_waveform(self, path: Path):
        """Read a bounded audio window asynchronously; ignore stale results."""
        if self.waveform_reload_after is not None:
            self.after_cancel(self.waveform_reload_after)
            self.waveform_reload_after = None
        self.waveform_request += 1
        self.waveform = []
        self.waveform_seconds = 0.
        self.waveform_start = 0.
        self.waveform_span = 120.
        self.waveform_total = 0.
        self.waveform_cursor = None
        self.waveinfo.config(text="載入波形…")
        self.wave_seek.config(state="disabled")
        self._draw_wave()
        self._request_waveform(path)

    def _request_waveform(self, path: Path):
        self.waveform_request += 1
        request = self.waveform_request
        start = self.waveform_start
        span = self.waveform_span
        def load():
            try:
                data = core.waveform_envelope(path, start_seconds=start, max_seconds=span)
            except Exception:
                data = {"samples":[], "duration_seconds":0., "start_seconds":start}
            self.events.put(("wave", request, data))
        threading.Thread(target=load, daemon=True).start()

    def _schedule_wave_reload(self):
        if not self.files:
            return
        self.waveform_request += 1
        if self.waveform_reload_after is not None:
            self.after_cancel(self.waveform_reload_after)
        self.waveform = []
        self.waveform_seconds = 0.
        self.waveinfo.config(text="更新波形…")
        self._draw_wave()
        self.waveform_reload_after = self.after(180, self._reload_waveform)

    def _reload_waveform(self):
        self.waveform_reload_after = None
        if self.files:
            selected = self.file_list.curselection()
            path = self.files[selected[0]] if selected and selected[0] < len(self.files) else self.files[0]
            self._request_waveform(path)

    def _update_wave_seek(self):
        self.waveform_seek_updating = True
        try:
            available = max(0., self.waveform_total - self.waveform_span)
            if available <= .001:
                self.wave_seek.config(state="disabled")
                self.wave_seek.set(0.)
            else:
                self.wave_seek.config(state="normal")
                self.wave_seek.set(self.waveform_start / available * 100.)
        finally:
            self.waveform_seek_updating = False

    def _wave_seek_changed(self, value):
        if self.waveform_seek_updating or self.waveform_total <= 0:
            return
        from .waveform_view import clamp_viewport
        available = max(0., self.waveform_total - self.waveform_span)
        target = available * float(value) / 100.
        start,span = clamp_viewport(target, self.waveform_span, self.waveform_total)
        if abs(start - self.waveform_start) >= .02:
            self.waveform_start, self.waveform_span = start,span
            self._schedule_wave_reload()

    def zoom_wave(self, factor, pixel=None):
        if self.waveform_total <= 0:
            return
        from .waveform_view import zoom_viewport, cursor_seconds
        anchor = (cursor_seconds(pixel,max(1,self.wavecanvas.winfo_width()),
                                 self.waveform_start,self.waveform_span)
                  if pixel is not None else self.waveform_cursor)
        start,span=zoom_viewport(self.waveform_start,self.waveform_span,
                                 self.waveform_total,factor,cursor=anchor)
        if (start,span)==(self.waveform_start,self.waveform_span):
            return
        self.waveform_start,self.waveform_span=start,span
        self._update_wave_seek()
        self._schedule_wave_reload()

    def pan_wave(self, direction):
        if self.waveform_total <= 0:
            return
        from .waveform_view import clamp_viewport
        start,span=clamp_viewport(self.waveform_start + direction*self.waveform_span*.75,
                                  self.waveform_span,self.waveform_total)
        if start!=self.waveform_start:
            self.waveform_start,self.waveform_span=start,span
            self._update_wave_seek()
            self._schedule_wave_reload()

    def reset_wave_zoom(self):
        if self.waveform_total <= 0:
            return
        from .waveform_view import clamp_viewport
        self.waveform_start,self.waveform_span=clamp_viewport(0.,120.,self.waveform_total)
        self._update_wave_seek()
        self._schedule_wave_reload()

    def _wave_click(self, event):
        if self.waveform_total <= 0:
            return
        from .waveform_view import cursor_seconds,format_time
        chosen=cursor_seconds(event.x,max(1,self.wavecanvas.winfo_width()),
                              self.waveform_start,self.waveform_span)
        self.waveform_cursor=min(chosen,self.waveform_total)
        self.ab_start.set(f"{self.waveform_cursor:.2f}")
        self.waveinfo.config(text=f"預聽起點 {format_time(self.waveform_cursor)}")
        self._draw_wave()

    def _wave_wheel(self, event):
        if event.delta:
            self.zoom_wave(2 if event.delta>0 else .5,event.x)
        return "break"

    def _schedule_wave_redraw(self, event=None):
        if self.waveform_redraw_after is not None:
            self.after_cancel(self.waveform_redraw_after)
        self.waveform_redraw_after=self.after(50,self._draw_wave)

    def _draw_wave(self):
        from .waveform_view import waveform_polygons,format_time
        self.waveform_redraw_after=None
        c=self.wavecanvas
        c.delete("all")
        w=max(1,c.winfo_width())
        h=max(1,c.winfo_height())
        for y in (h*.25,h*.75):
            c.create_line(0,y,w,y,fill="#293743",width=1)
        c.create_line(0,h*.5,w,h*.5,fill="#435363",width=1)
        if self.waveform:
            start=self.waveform_start
            end=start+self.waveform_seconds
            for step in range(1,5):
                x=w*step/5
                c.create_line(x,0,x,h,fill="#263440",width=1)
            outer,body=waveform_polygons(self.waveform,w,h,margin=11)
            if len(outer)>=6:
                c.create_polygon(*outer,fill="#318C9F",outline="")
            if len(body)>=6:
                c.create_polygon(*body,fill=ACCENT,outline="")
            for step in range(5):
                frac=step/4
                x=6+(w-12)*frac
                anchor="w" if step==0 else "e" if step==4 else "center"
                c.create_text(x,h-8,text=format_time(start+self.waveform_seconds*frac),
                              anchor=anchor,fill="#A8B7C2",font=(FONT,8))
            if self.waveform_cursor is not None and start<=self.waveform_cursor<=end:
                x=(self.waveform_cursor-start)/max(.001,self.waveform_seconds)*w
                c.create_line(x,0,x,h-20,fill="#F4CB86",width=1)
                c.create_polygon(x-4,2,x+4,2,x,8,fill="#F4CB86",outline="")
        else:
            c.create_text(w/2,h/2,text="載入波形…" if self.files else
                          "拖入或新增音檔即可預覽波形",
                          fill="#78919D",font=(FONT,10))

    def pick_folder(self):
        folder=filedialog.askdirectory(title="指定輸出資料夾")
        if folder:
            self.destination.set(folder)

    def log(self,msg):
        self.logbox.configure(state="normal")
        self.logbox.insert("end",msg+"\n")
        if int(self.logbox.index("end-1c").split(".")[0])>500:
            self.logbox.delete("1.0","200.0")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def start(self):
        if self.is_running:
            return
        if not self.files and self.tool not in ('ai_status', 'setup'):
            messagebox.showinfo("尚未加入音檔","請先新增至少一個音檔。")
            return
        opts={k:v.get() for k,v in self.option_vars.items()}
        opts["destination"]=self.destination.get()
        try:
            # Measured mic matching uses SoundFile; pure rename and checks
            # do not require FFmpeg at all.
            # Neural tools, WPE, pYIN, beat tracking and music analysis operate
            # directly on WAV/FLAC/AIFF via SoundFile. They should not refuse
            # to start merely because the optional FFmpeg decoder is absent.
            # Their worker can request FFmpeg later for incompatible sources.
            requires_ffmpeg = {
                'convert', 'denoise', 'residual', 'declick', 'declip', 'deess',
                'loudscan', 'normalize', 'silence', 'inspect', 'quality',
                'compare', 'align',
            }
            needs_ffmpeg = self.tool in requires_ffmpeg or (
                self.tool == 'mic' and not opts.get('reference_path'))
            if needs_ffmpeg:
                core.require_ffmpeg()
        except core.ToolkitError as e:
            messagebox.showerror("缺少 FFmpeg",str(e))
            return
        tool=self.tool
        if tool in ("compare","align","verify") and len(self.files)!=2:
            messagebox.showinfo("比較音檔","音檔比對請加入剛好 2 個檔案。")
            return
        self.is_running=True
        core.CANCEL.clear()
        self.runbtn.configure(state="disabled",bg="#3B5260")
        self.state_label.config(text="處理中…",fg=ACCENT)
        if tool != 'rhythm':
            self.log("—"*42)
            self.log(f"開始｜{TOOL_INFO[tool][0]}｜{len(self.files)} 個檔案")
        files=list(self.files)
        total=1 if tool in ('ai_status', 'setup') else len(files)
        def worker():
            from .result_view import format_result
            succeeded=0
            summaries=[]
            errors=[]
            try:
                if tool == 'setup':
                    import json
                    from apt.diagnostics import collect
                    report = collect(check_gui=False)
                    summaries.append(('環境檢查',format_result('setup',report)))
                    succeeded = 1
                elif tool=='ai_status':
                    import json
                    from apt.worker import run_job
                    result=run_job('status', model_dir=opts.get('model_dir'),
                                   runtime_python=opts.get('runtime_python'), cancelled=core.CANCEL.is_set)
                    summaries.append(('AI 模型狀態',format_result('ai_status',result)))
                    succeeded = 1
                elif tool=="rhythm":
                    import json
                    from .rhythm_result import format_summary
                    summaries=[]
                    for file in files:
                        if core.CANCEL.is_set():
                            break
                        try:
                            raw=json.loads(core.estimate_bpm_key(file))
                            from .rhythm_result import summary_lines
                            summaries.append((file.name,summary_lines(format_summary(raw))))
                            succeeded+=1
                        except Exception as exc:
                            errors.append((file.name,str(exc)))
                elif tool=="rename":
                    results=core.copy_renamed(files,opts,lambda x:self.events.put(("log",x)))
                    succeeded=len(results)
                    if results:
                        self.events.put(("output",results[-1]))
                        summaries.append(('批次重新命名',f'完成 {len(results)} 個檔案\n輸出資料夾：{results[0].parent}'))
                elif tool in ("compare", "align", "verify"):
                    if tool == 'verify':
                        import json
                        from apt.validation import compare_audio
                        msg=json.dumps(compare_audio(files[0], files[1], core.CANCEL.is_set), ensure_ascii=False, indent=2)
                    else:
                        msg=(core.compare_files(files[0],files[1]) if tool=="compare"
                             else core.estimate_alignment(files[0],files[1]))
                    path=core.save_report(files[0], '_'+tool, opts, msg)
                    summaries.append(('檔案比對',format_result(tool,msg,path)))
                    self.events.put(("output",path))
                    succeeded=len(files)
                else:
                    for i,p in enumerate(files,1):
                        if core.CANCEL.is_set():
                            break
                        self.events.put(("log",f"[{i}/{len(files)}] {p.name}"))
                        try:
                            msg,generated=core.run_tool(tool,p,opts)
                            summaries.append((p.name,format_result(tool,msg,generated)))
                            if generated:
                                self.events.put(("output",generated,p))
                            succeeded+=1
                        except core.ToolkitError as e:
                            errors.append((p.name,str(e)))
                            if "已取消" in str(e):
                                break
                        except Exception as e:
                            errors.append((p.name,str(e)))
                self.events.put(("result_batch",tool,summaries,errors))
                self.events.put(("finished",succeeded,total,core.CANCEL.is_set()))
            except Exception as e:
                errors.append(('操作失敗',str(e)))
                self.events.put(("result_batch",tool,summaries,errors))
                self.events.put(("finished",succeeded,total,core.CANCEL.is_set()))
        self.worker_thread=threading.Thread(target=worker,daemon=False)
        self.worker_thread.start()

    def test_installed_ai(self):
        if self.is_running or self.ai_verify_running or self.ai_install_running:
            return
        from apt.worker import app_directory
        root=app_directory()
        interpreter=root/'.apt-ai'/'Scripts'/'python.exe' if os.name=='nt' else root/'.apt-ai'/'bin'/'python'
        script=root/'scripts'/'verify_optional_ai.py'
        if not interpreter.is_file() or not script.is_file():
            messagebox.showinfo('AI 本機實測',
                '找不到已安裝的 AI Python 或驗收程式。請先執行所需模組的 setup_ai_windows.bat。')
            return
        chosen=self.ai_test_module.get()
        if chosen not in ('denoise','split','meter','pitch','dereverb'):
            return
        if not messagebox.askokcancel('AI 本機實測',
                f'將使用已安裝的 {chosen} 模組處理 8 秒合成音，不讀取私人錄音，也不下載模型。\\nCPU 模型可能需要較長運算時間。是否執行？'):
            return
        self.ai_verify_running=True
        self.log(f'AI 模型實際推論測試開始：{chosen}（不下載模型）')
        def work():
            proc=None
            try:
                flags={'creationflags':getattr(subprocess,'CREATE_NO_WINDOW',0)} if os.name=='nt' else {}
                env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
                from .ai_control import external_popen
                proc=external_popen([str(interpreter),str(script),'--module',chosen],
                    cwd=str(root),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',
                    env=env,**flags)
                self.ai_verify_process=proc
                out,err=proc.communicate(timeout=900)
                self.events.put(('ai_verify_result',chosen,proc.returncode,out[-3000:],err[-3000:]))
            except subprocess.TimeoutExpired:
                if proc is not None and proc.poll() is None:
                    self._kill_ai_test(proc)
                self.events.put(('ai_verify_result',chosen,1,'','AI 模型自測逾時（15 分鐘上限）'))
            except Exception as exc:
                self.events.put(('ai_verify_result',chosen,1,'',str(exc)))
            finally:
                self.ai_verify_process=None
        threading.Thread(target=work,daemon=True).start()

    @staticmethod
    def _kill_ai_test(proc):
        if proc.poll() is not None:
            return
        if os.name=='nt':
            try:
                subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=4,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            except (OSError,subprocess.TimeoutExpired):
                pass
        if proc.poll() is None:
            proc.terminate()

    def install_ffmpeg_windows(self):
        """Open the shipped interactive installer; never download on startup."""
        if os.name != 'nt':
            messagebox.showinfo('FFmpeg', '此安裝工具僅適用於 Windows。')
            return
        from apt.worker import app_directory
        batch=app_directory() / 'setup_ffmpeg_windows.bat'
        if not batch.is_file():
            messagebox.showerror('FFmpeg', f'找不到安裝工具：{batch}')
            return
        if not messagebox.askyesno('安裝／修復 FFmpeg',
                '將開啟 Windows 命令視窗，並在視窗中再次要求確認安裝 FFmpeg。'
                '安裝後請重新開啟 Audio Post Toolkit。是否繼續？'):
            return
        try:
            os.startfile(str(batch))
            self.log('已開啟 FFmpeg 選裝工具；安裝完成後請重新啟動軟體。')
        except OSError as exc:
            messagebox.showerror('FFmpeg', str(exc))

    def install_selected_ai(self):
        if self.is_running or self.ai_install_running or self.ai_verify_running:
            return
        from apt.worker import app_directory
        from .ai_control import install_command, MODELS
        root = app_directory()
        module = self.ai_test_module.get()
        requires_weights = module in MODELS
        message = (
            f'即將在獨立 .apt-ai 環境中安裝 {module}。\\n'
            + ('此功能需要另外下載官方模型與 PyTorch，可能占用數 GB 磁碟。\\n'
               if requires_weights else '此模組只需獨立安裝相關 Python 套件。\\n')
            + '不會改動原始音檔，並且不會把 AI 套件塞進主程式。是否開始？'
        )
        if not messagebox.askokcancel('安裝選定的 AI 模組', message):
            return
        try:
            args = install_command(root, module, download_models=requires_weights)
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror('AI 安裝工具', str(exc))
            return
        self.ai_install_running = True
        self.log(f'開始安裝 {module}，請保持網路連線；完成後可直接使用此模組。')
        self.state_label.config(text=f'安裝 {module}…', fg=WARNING)
        def worker():
            import tempfile
            proc = None
            try:
                with tempfile.TemporaryDirectory(prefix='.apt_ai_gui_') as directory:
                    logfile = Path(directory) / 'install.log'
                    with logfile.open('wb') as log:
                        from .ai_control import external_popen
                        proc = external_popen(
                            args, cwd=str(root), stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                        self.ai_install_process = proc
                        try:
                            proc.wait(timeout=1800)
                        except subprocess.TimeoutExpired:
                            self._kill_ai_test(proc)
                            self.events.put(('ai_install_result', module, False,
                                             '安裝已達 30 分鐘限制，已停止。'))
                            return
                    with logfile.open('rb') as log:
                        log.seek(max(0, logfile.stat().st_size - 4000))
                        detail = log.read().decode('utf-8', errors='replace')
                    success = proc.returncode == 0
                    self.events.put(('ai_install_result', module, success, detail))
            except Exception as exc:
                self.events.put(('ai_install_result', module, False,
                                 f'{type(exc).__name__}: {exc}'))
            finally:
                self.ai_install_process = None
        threading.Thread(target=worker, daemon=True).start()

    def start_technical_qa(self):
        if self.qa_running or self.is_running:
            return
        source=selected_preview_path(self.files,self.file_list.curselection(),self.output_pairs)
        processed=selected_preview_path(self.files,self.file_list.curselection(),self.output_pairs,processed=True)
        if not source or not processed or not processed.is_file():
            messagebox.showinfo('技術驗收報告','請先處理選取的音檔，並確認有對應的輸出檔。')
            return
        folder=self.destination.get()
        self.qa_running=True
        self.log('技術驗收：讀取來源與輸出音檔，產生本機 JSON 報告…')
        def worker():
            try:
                from .acceptance import publish_report
                path,report=publish_report(source,processed,folder)
                self.events.put(('qa_ready',str(path),report['technical_integrity_pass'],None))
            except Exception as exc:
                self.events.put(('qa_ready',None,False,f'{type(exc).__name__}: {exc}'))
        threading.Thread(target=worker,daemon=True).start()

    def test_output_device(self):
        if self.playback_in_progress:
            return
        if not messagebox.askokcancel('實機聲音測試',
                '將使用電腦預設播放設備播放 1 秒、-30 dBFS 的低音量測試音。\n請先將音量調低，確認喇叭／耳機已連接。'):
            return
        self.playback_in_progress = True
        self.log('開始手動輸出設備測試；不使用麥克風、不錄音、不上傳音訊。')
        def worker():
            try:
                from .device_check import play_speaker_test
                result = play_speaker_test()
                self.events.put(('device_test', result, None))
            except Exception as exc:
                self.events.put(('device_test', None, f'{type(exc).__name__}: {exc}'))
        threading.Thread(target=worker, daemon=True).start()

    def cancel_work(self):
        if self.is_running:
            core.cancel()
            self.state_label.config(text="正在取消…",fg=WARNING)
        if self.ai_verify_running and self.ai_verify_process is not None:
            self._kill_ai_test(self.ai_verify_process)
            self.log('已要求中止 AI 模型自測。')
        if self.ai_install_running and self.ai_install_process is not None:
            self._kill_ai_test(self.ai_install_process)
            self.log('已要求中止選裝 AI 模組安裝。')

    def _drain_events(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event[0]=="log":
                    self.log(event[1])
                elif event[0]=="output":
                    self.output_file=event[1]
                    if len(event)>2 and event[1].is_file() and event[1].suffix.lower() in core.AUDIO_TYPES:
                        self.output_pairs[str(event[2].resolve())]=event[1]
                elif event[0]=='ab_ready':
                    _,request,a,b,details=event
                    if request==self.ab_request:
                        try:
                            from .ab_preview import ABPlayer
                            self.ab_player=ABPlayer(a,b,sample_rate=details['playback_sample_rate'])
                            self.ab_player.start()
                            self.log('同步 A/B 播放中：A 原音；切換不重設播放位置。')
                            self.log(f"預聽：B 補償 {details['processed_offset_ms']:.1f} ms；B 增益 {details['b_gain_db']:.2f} dB；共同增益 {details['common_gain_db']:.2f} dB。音檔未修改。")
                        except Exception as exc:
                            self.stop_preview()
                            self.log(f'A/B 無法播放：{exc}')
                elif event[0]=='result_batch':
                    from .result_view import format_batch
                    _,completed_tool,results,errors=event
                    label=TOOL_INFO[completed_tool][0]
                    body=format_batch(results,errors)
                    if errors:
                        messagebox.showwarning(label + '：完成結果',body)
                    elif results:
                        messagebox.showinfo(label + '：完成結果',body)
                elif event[0]=='ai_install_result':
                    _,module,success,detail=event
                    self.ai_install_running=False
                    self.state_label.config(text='AI 安裝完成' if success else 'AI 安裝失敗',
                                            fg=GOOD if success else WARNING)
                    if detail.strip(): self.log(detail[-1700:])
                    self.log(f'{module}：安裝{"成功" if success else "未完成"}')
                    if success:
                        messagebox.showinfo('AI 安裝完成',
                            f'{module} 已安裝在獨立 AI 環境。現在可以選擇該功能直接處理錄音。')
                        # Force tool options to refresh their default model path.
                        self.saved_options.pop('ai_denoise' if module=='denoise' else module,None)
                    else:
                        messagebox.showwarning('AI 安裝失敗',
                            f'{module} 安裝未完成。請確認網路與磁碟空間，或使用 setup_ai_windows.bat 重試。')
                elif event[0]=='ai_verify_result':
                    _,name,returncode,out,error=event
                    self.ai_verify_running=False
                    self.log(f'{name} 模型推論自測：{"成功" if returncode==0 else "失敗"}')
                    if out.strip(): self.log(out.strip())
                    if error.strip(): self.log(error.strip())
                    if returncode==0:
                        messagebox.showinfo('AI 自測成功',
                            f'{name} 已完成合成測試音的本機推論。這不代表對真人錄音的音質驗收。')
                    else:
                        messagebox.showwarning('AI 自測失敗',
                            f'{name} 本機模型運算未通過。請檢查模組與模型是否完整安裝。')
                elif event[0]=='qa_ready':
                    _,path,ok,error=event
                    self.qa_running=False
                    if error:
                        self.log(f'技術驗收報告失敗：{error}')
                        messagebox.showerror('技術驗收報告',error)
                    else:
                        self.log(f'本機技術驗收報告已保存：{path}（基本完整性：{"通過" if ok else "需檢查"}）')
                        messagebox.showinfo('技術驗收報告',f'已儲存：\n{path}\n\n基本完整性：{"通過" if ok else "需檢查"}\n注意：本報告不等同聽感驗收。')
                elif event[0]=='device_test':
                    _,result,error=event
                    self.playback_in_progress = False
                    if error:
                        self.log(f'輸出設備測試失敗：{error}')
                        messagebox.showerror('播放設備測試', error)
                    elif result:
                        heard = messagebox.askyesno(
                            '實機聲音驗收',
                            '是否確實從預設耳機或喇叭聽到 1 秒測試音？\n'
                            '只有你親自確認，才會記錄這次播放測試通過。')
                        self.playback_confirmed_in_session = bool(heard)
                        self.log('本次播放測試：使用者確認有聲音' if heard else
                                 '本次播放測試：未確認聽到聲音（需檢查音效裝置與音量）')
                elif event[0]=="wave":
                    _,req,data=event
                    if req==self.waveform_request:
                        from .waveform_view import clamp_viewport,format_time
                        self.waveform = data.get("samples", []) if isinstance(data, dict) else []
                        self.waveform_seconds = data.get("duration_seconds", 0.) if isinstance(data, dict) else 0.
                        self.waveform_total = data.get("source_duration_seconds", 0.) if isinstance(data, dict) else 0.
                        if self.waveform_total:
                            self.waveform_start,self.waveform_span = clamp_viewport(
                                self.waveform_start,self.waveform_span,self.waveform_total)
                        self.waveinfo.config(text=(f"{format_time(self.waveform_start)} – "
                            f"{format_time(self.waveform_start+self.waveform_seconds)} / "
                            f"{format_time(self.waveform_total)}" if self.waveform else "無法預覽"))
                        self._update_wave_seek()
                        self._draw_wave()
                elif event[0]=="finished":
                    _,n,total,cancelled=event
                    self.is_running=False
                    self.runbtn.configure(state="normal",bg=ACCENT)
                    self.state_label.config(text="已取消" if cancelled else f"完成 {n}/{total}",fg=WARNING if cancelled or n<total else GOOD)
                    self.log(f"工作結束｜成功 {n}/{total}"+("｜使用者取消" if cancelled else ""))
        except queue.Empty:
            pass
        self.after(100,self._drain_events)

    def play_audio(self, output: bool):
        path=selected_preview_path(self.files, self.file_list.curselection(), self.output_pairs, processed=output)
        if not path or not path.is_file() or path.suffix.lower()==".txt":
            messagebox.showinfo("無法預聽","請先選取音檔，或完成一次音訊輸出。")
            return
        player=core.find_executable("ffplay")
        if not player:
            messagebox.showinfo("缺少預聽播放器","請安裝含 ffplay 的 FFmpeg 版本；音訊處理本身不受影響。")
            return
        self.stop_preview()
        try:
            flags={"creationflags":getattr(subprocess,"CREATE_NO_WINDOW",0)} if os.name=="nt" else {}
            start=float(self.ab_start.get() or 0)
            if not (0 <= start < float("inf")):
                start=0.
            self.preview_process=subprocess.Popen(
                [player,"-nodisp","-autoexit","-loglevel","error","-ss",str(start),str(path)],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**flags)
        except OSError as e:
            messagebox.showerror("無法播放",str(e))

    def start_ab(self):
        if not self.files:
            messagebox.showinfo('同步 A/B','請先選擇已處理過的來源音檔。')
            return
        source=selected_preview_path(self.files, self.file_list.curselection(), self.output_pairs)
        processed=selected_preview_path(self.files, self.file_list.curselection(), self.output_pairs, processed=True)
        if not processed or not processed.is_file():
            messagebox.showinfo('同步 A/B','選取的來源尚無對應音訊輸出；請先處理此檔案。')
            return
        try:
            from .ab_preview import choose_output_rate
            playback_rate = choose_output_rate()
            start=float(self.ab_start.get()); duration=float(self.ab_seconds.get())
            offset=float(self.ab_offset.get()); matched=bool(self.ab_match.get())
            if start<0 or not 0.1<=duration<=120:
                raise ValueError('起點需大於等於 0，預聽秒數需為 0.1–120。')
        except Exception as exc:
            messagebox.showerror('同步 A/B',f'{exc}\n此功能需要選裝 sounddevice。')
            return
        self.stop_preview()
        request=self.ab_request
        self.log(f'準備同步預聽片段…使用輸出設備預設 {playback_rate} Hz')
        def prepare():
            try:
                from .ab_preview import prepare_pair
                a,b,details=prepare_pair(source,processed,start,duration,processed_offset_ms=offset,match_loudness=matched,return_info=True,sample_rate=playback_rate)
                self.events.put(('ab_ready',request,a,b,details))
            except Exception as exc:
                self.events.put(('log',f'A/B 準備失敗：{exc}'))
        threading.Thread(target=prepare,daemon=True).start()

    def select_ab(self, value):
        if self.ab_player is not None:
            self.ab_player.select(value)
            self.log('A 原音' if value==0 else 'B 輸出')

    def stop_preview(self):
        self.ab_request += 1
        if self.ab_player is not None:
            self.ab_player.close()
            self.ab_player=None
        if self.preview_process and self.preview_process.poll() is None:
            self.preview_process.terminate()
        self.preview_process=None

    def _close(self):
        if self.is_running:
            core.cancel()
        if self.ai_verify_process is not None:
            self._kill_ai_test(self.ai_verify_process)
        if self.ai_install_process is not None:
            self._kill_ai_test(self.ai_install_process)
        self.stop_preview()
        if self.waveform_reload_after is not None:
            self.after_cancel(self.waveform_reload_after)
        if self.waveform_redraw_after is not None:
            self.after_cancel(self.waveform_redraw_after)
        self.destroy()


def main():
    App().mainloop()
