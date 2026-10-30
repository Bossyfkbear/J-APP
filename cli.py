"""Independent command-line entry point for Audio Post Toolkit modules."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from aptk import core

TOOLS = ('convert','denoise','residual','ai_denoise','dereverb','declick','declip','deess','mic','loudscan','normalize','silence','inspect','quality','rhythm','pitch','meter','split','chords','progression','ai_status')

def main(argv=None):
    # Redirected Windows consoles may use a code page without Chinese glyphs.
    # Reporting a successful conversion must not turn it into a failed job.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(description='Audio Post Toolkit: offline batch processing')
    parser.add_argument('tool', choices=TOOLS)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--destination', default='')
    parser.add_argument('--model-dir', default='')
    parser.add_argument('--runtime-python', default='', help='Optional external AI Python executable')
    parser.add_argument('--model-name', default='')
    parser.add_argument('--split-mode', choices=('vocal','four'), default='vocal')
    parser.add_argument('--format', dest='fmt', default='wav', choices=('wav','flac','aiff','mp3','aac'))
    parser.add_argument('--depth', default='auto', choices=('auto','16','24','32','32f','64f'))
    parser.add_argument('--rate', default='保留')
    parser.add_argument('--channels', default='保留')
    parser.add_argument('--noise-amount', default='12')
    parser.add_argument('--strength', default='0.5', help='WPE dry/wet mix (0 to 1)')
    parser.add_argument('--mic-strength', default='65')
    parser.add_argument('--reference-path', default='', help='Optional matching-microphone target WAV/FLAC/AIFF (same rate as source)')
    parser.add_argument('--target-i', default='-16')
    parser.add_argument('--target-tp', default='-1.5')
    parser.add_argument('--target-lra', default='11')
    args = parser.parse_args(argv)
    opts = vars(args)
    opts['destination'] = args.destination
    core.CANCEL.clear()
    failures = 0
    for src in args.files:
        if not src.is_file():
            print(f'ERROR: missing file: {src}', file=sys.stderr)
            failures += 1
            continue
        try:
            message, output = core.run_tool(args.tool, src, opts)
            print(f'{message}\nOUTPUT: {output}')
        except (core.ToolkitError, OSError, ValueError, RuntimeError, ImportError) as exc:
            print(f'ERROR: {src}: {exc}', file=sys.stderr)
            failures += 1
    return 1 if failures else 0

if __name__ == '__main__':
    raise SystemExit(main())
