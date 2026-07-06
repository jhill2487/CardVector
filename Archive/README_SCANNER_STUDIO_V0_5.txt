Putnam Scanner Studio v0.5 - Python 3.14 server patch

What changed:
- Replaces scanner_server.py only.
- Removes import cgi, which fails in Python 3.14.
- Keeps the same endpoints and workflow:
  http://127.0.0.1:8765
  /api/upload
  /api/scan

Install/use:
1. Extract this ZIP into:
   C:\Users\JaredHill\Personal\PutnamCollectibles

2. Allow it to overwrite scanner_server.py.

3. Start server:
   python scanner_server.py

4. Open Chrome/Edge:
   http://127.0.0.1:8765

5. Press Ctrl+F5 to force refresh.

Expected server startup:
Putnam Scanner Studio v0.5 running at http://127.0.0.1:8765
Python 3.14 compatible: no cgi module used
