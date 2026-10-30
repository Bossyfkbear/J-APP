import argparse, json
from .core import convert,analyze,detect_tempo
from .music import detect_key,detect_chords
from .harmony import progression
from .benchmark import benchmark_tempo,benchmark_chords,benchmark_keys
from .models import denoise, runtime_status, separate_vocals
from .quality import inspect_audio
from .loudness import measure_loudness

def main():
    ap=argparse.ArgumentParser(description="Audio Post Toolkit 0.5 — offline CLI")
    sub=ap.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("convert"); c.add_argument("source"); c.add_argument("destination"); c.add_argument("--sample-rate",type=int); c.add_argument("--channels",type=int); c.add_argument("--codec")
    dn=sub.add_parser("denoise-ai"); dn.add_argument("source"); dn.add_argument("destination"); dn.add_argument("--model-dir",required=True)
    sep=sub.add_parser("separate-vocals"); sep.add_argument("source"); sep.add_argument("destination"); sep.add_argument("--model-dir",required=True)
    st=sub.add_parser("ai-status", help="Check optional AI runtime and local model availability")
    st.add_argument("--model-dir")
    q=sub.add_parser("quality"); q.add_argument("source")
    v=sub.add_parser("verify"); v.add_argument("source"); v.add_argument("output")
    l=sub.add_parser("loudness"); l.add_argument("source")
    a=sub.add_parser("analyze"); a.add_argument("source")
    t=sub.add_parser("tempo"); t.add_argument("source")
    k=sub.add_parser("key"); k.add_argument("source")
    h=sub.add_parser("chords"); h.add_argument("source"); h.add_argument("--window-seconds",type=float,default=1.0)
    p=sub.add_parser("progression"); p.add_argument("source"); p.add_argument("--key"); p.add_argument("--window-seconds",type=float,default=1.0)
    bk=sub.add_parser("benchmark-keys"); bk.add_argument("manifest")
    bt=sub.add_parser("benchmark-tempo"); bt.add_argument("manifest")
    bc=sub.add_parser("benchmark-chords"); bc.add_argument("manifest"); bc.add_argument("--window-seconds",type=float,default=1.0)
    args=ap.parse_args()
    if args.cmd=="ai-status": print(json.dumps(runtime_status(args.model_dir),ensure_ascii=False,indent=2))
    elif args.cmd=="denoise-ai": print(json.dumps(denoise(args.source,args.destination,args.model_dir),indent=2))
    elif args.cmd=="separate-vocals": print(json.dumps(separate_vocals(args.source,args.destination,args.model_dir),indent=2))
    elif args.cmd=="benchmark-keys": print(json.dumps(benchmark_keys(args.manifest),indent=2))
    elif args.cmd=="benchmark-tempo": print(json.dumps(benchmark_tempo(args.manifest),indent=2))
    elif args.cmd=="benchmark-chords": print(json.dumps(benchmark_chords(args.manifest,args.window_seconds),indent=2))
    elif args.cmd=="convert": print(convert(args.source,args.destination,args.sample_rate,args.channels,args.codec))
    elif args.cmd=="verify":
        from .validation import compare_audio
        print(json.dumps(compare_audio(args.source,args.output),ensure_ascii=False,indent=2))
    elif args.cmd=="quality": print(json.dumps(inspect_audio(args.source),ensure_ascii=False,indent=2))
    elif args.cmd=="loudness": print(json.dumps(measure_loudness(args.source),ensure_ascii=False,indent=2))
    elif args.cmd=="analyze": print(json.dumps(analyze(args.source),ensure_ascii=False,indent=2))
    elif args.cmd=="tempo": print(json.dumps(detect_tempo(args.source),indent=2))
    elif args.cmd=="key": print(json.dumps(detect_key(args.source),ensure_ascii=False,indent=2))
    elif args.cmd=="progression": print(json.dumps(progression(args.source,args.window_seconds,args.key),ensure_ascii=False,indent=2))
    elif args.cmd=="chords": print(json.dumps(detect_chords(args.source,args.window_seconds),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
