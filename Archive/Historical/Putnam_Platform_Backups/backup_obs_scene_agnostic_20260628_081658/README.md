# Putnam Capture v0.2

Putnam Capture is a platform proof-of-concept for capturing still images from OBS.
OBS owns the camera feed; Putnam Capture asks OBS WebSocket for JPEG screenshots of
the card capture scene.

This version does not integrate into Putnam OS yet.

## OBS Requirements

OBS must be open before launching Putnam Capture.

Enable OBS WebSocket:

1. Open OBS.
2. Go to `Tools > WebSocket Server Settings`.
3. Enable the WebSocket server.
4. Use the default port: `4455`.
5. Leave the password blank for the default Putnam Capture setup, or launch with
   `--password-prompt` if you enable a password.

The required OBS scene name is:

```text
03 - Card Capture
```

That scene should contain the DroidCam OBS source.

## Install Dependency

Putnam Capture v0.2 requires `obsws-python`:

```bat
py -m pip install obsws-python
```

If the dependency is missing, the app prints that install command and exits.

## Launch

Run:

```bat
%USERENVIRONMENT%\Putnam_Platform\tools\Run_Putnam_Capture.bat
```

If `USERENVIRONMENT` is not set, the app falls back to:

```text
%USERPROFILE%\OneDrive\PutnamCollectibles
```

Default OBS connection:

```text
host: localhost
port: 4455
password: prompted by the launcher
```

The launcher uses a normal command-window prompt:

```text
OBS WebSocket password:
```

Optional examples:

```bat
Run_Putnam_Capture.bat --password-prompt
Run_Putnam_Capture.bat --host localhost --port 4455 --scene "03 - Card Capture"
```

## Controls

- Spacebar: capture the current OBS scene frame as a JPEG.
- Q: close the app.
- Escape: close the app.

The console prints each captured filename.

## Output

Each run creates a new session folder:

```text
<root>\Putnam_OS\Incoming Files\Capture_Sessions\<YYYY-MM-DD_HHMMSS>\
```

Images are saved to:

```text
<session>\images\000001.jpg
<session>\images\000002.jpg
<session>\images\000003.jpg
```

The app also writes:

- `session.json`
- `capture_log.csv`

`session.json` includes:

- `start_time`
- `end_time`
- `obs_scene`
- `output_folder`
- `image_count`
- `capture_method = "obs_websocket"`

`capture_log.csv` includes:

- `filename`
- `timestamp`
- `obs_scene`
- `status`

The final image output folder is printed when the app closes.

## Import Into CardUploader

After capture, open CardUploader and import from the printed `images` folder:

```text
<root>\Putnam_OS\Incoming Files\Capture_Sessions\<YYYY-MM-DD_HHMMSS>\images
```

Select the session folder created for the work session, then process the numbered
JPEGs in order.
