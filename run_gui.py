"""PyInstaller entry point for the desktop application."""
if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--ai-worker':
        from apt.worker import execute
        raise SystemExit(execute(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == '--diagnostics':
        from apt.diagnostics import write_report
        report = write_report(sys.argv[2], check_gui=True)
        raise SystemExit(0 if report['gui'].get('ok') else 1)
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        from apt.diagnostics import write_audio_smoke
        report = write_audio_smoke(sys.argv[2])
        raise SystemExit(0 if report['ok'] else 1)
    from aptk.ui import main
    main()
