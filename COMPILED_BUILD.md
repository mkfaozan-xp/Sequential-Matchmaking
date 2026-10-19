# Compiled controller

Use CPython 3.12 (reference 3.12.14):

```bash
python3.12 -S -B tools/run_coordinated_compiled.py --mode coordinated < runtime/examples/refreshed_match_request.json
```

The same command accepts `--mode conservative`, the default. On Windows use CMD input redirection and `py -3.12`.

The current controller adds three checked-hash bytecode files to the retained foundation (17 runtime and 117 research files), for 137 total. Research bytecode preserves build provenance; serving imports the runtime foundation and current controller. Original source and immutable JSON models remain included. Launchers verify source hashes, bytecode hashes, interpreter magic and source-hash headers.

Compilation does not improve accuracy or fit weights. This is not a native executable; Python 3.14 cannot execute this 3.12 bytecode target. The current model was independently refit from flat inputs with identical bytes.

`results/coordinated/transport.json` records 720 restarted CLI calls with identical source/compiled actions and outcomes across six known worlds. These are parity checks, not independent efficacy or actual Docker/Windows execution.

`tools/verify_compilation.py` checks the retained foundation. `tools/check_coordinated_cli.py --output EXTERNAL_PATH` exercises the current source/compiled controller and writes new evidence outside the release. Windows and constrained Docker remain unverified until actually executed.
