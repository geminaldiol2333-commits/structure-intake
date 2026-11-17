# Grounding for the window launch

A person reaches the comparison page only by running `scratch/intake-prototypes/prototype.py serve`. `__main__` defaults the port to 8765 and calls `serve(port)`. `serve` binds `ThreadingHTTPServer` to `127.0.0.1` and prints `http://127.0.0.1:<port>/`. The process then blocks in `serve_forever`. Opening that URL returns `index.html`. The title is `结构式提取原型`. The scheme bar is empty until `main()` fetches `out/results.json` and creates the buttons.

`run` builds `out/results.json` and talks to ChemDraw. `serve` does not. `overlay` does not start the page. Copy is `POST /api/copy` inside `Handler.do_POST`, which empties the Windows clipboard. MOL writes `ChemDraw Interchange Format` plus format 13. SMILES and SMARTS write format 13 only.

`verify_intake.py launch --port 8766` starts `prototype.py serve --port <port>` and refuses to kill a listener it does not own. `doctor` requires the command line to contain `prototype.py`, `serve`, and `--port <port>`. Cleanup kills only that recorded pid.

pywebview is installed for `C:\Python314\python.exe`. WebView2 157.0.4314.42 is installed. Do not change `tools/` or the recognition schemes. Do not start ChemDraw from the window launch.

The ordinary person must see a window. They must not type a URL or a command. Closing the window stops only the server that window started. The verification helper must still be able to start a port-only server with no window.
