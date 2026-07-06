# Project Launcher Scripts

Patch P0.4 added one-click launcher scripts to the project root.

## Scripts

### start_lookup_backend.bat
Starts the Putnam Pokemon Lookup backend on port 8790.

### restart_lookup_backend.bat
Stops any process listening on port 8790, then starts the backend again.

### open_lookup_viewer.bat
Opens the local backend viewer in the browser.

### open_chrome_extensions.bat
Opens Chrome Extensions so the unpacked extension can be reloaded.

### run_portability_audit.bat
Runs the portability audit.

### fix_data_sources_portability.bat
Rewrites backend/data_sources.json for the current PC username/path.

## Normal workflow

1. Double-click restart_lookup_backend.bat
2. Open chrome://extensions and reload the extension
3. Use the Putnam Pokemon Lookup Overlay
