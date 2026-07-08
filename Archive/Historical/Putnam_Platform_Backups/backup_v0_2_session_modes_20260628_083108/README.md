# Putnam Capture

Putnam Capture is a platform proof-of-concept for capturing still JPEGs from an OBS scene.
OBS owns the camera/source stack; Putnam Capture captures whatever is visible in the selected
OBS scene.

This version does not integrate into Putnam OS yet.

## OBS Requirements

OBS must be open before launching Putnam Capture.

Enable OBS WebSocket:

1. Open OBS.
2. Go to `Tools > WebSocket Server Settings`.
3. Enable the WebSocket server.
4. Use the default port: `4455`.
5. Use the password configured in OBS WebSocket.

Default OBS scene:

```text
03 - Card Capture
```

The scene can contain any OBS source: DroidCam, iOS Camera, OBS Camera, a webcam,
a capture card, or any other visible source.

## Settings

Putnam Capture creates and reads:

```text
%USERENVIRONMENT%\Putnam_Platform\capture\capture_settings.json
```

Default settings:

```json
{
  "obs_host": "localhost",
  "obs_port": 4455,
  "obs_scene": "03 - Card Capture",
  "capture_method": "obs_scene_screenshot",
  "save_full_frame": true,
  "save_cropped_frame": false
}
```

Cropping is not implemented yet. `save_cropped_frame` is reserved for a future update.

## Install Dependency

Putnam Capture requires `obsws-python`:

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

On startup, Putnam Capture lists available OBS scenes. Press Enter to use the configured
default scene, or type a different scene name exactly as it appears in OBS.

Optional examples:

```bat
Run_Putnam_Capture.bat --host localhost --port 4455
Run_Putnam_Capture.bat --scene "03 - Card Capture" --no-scene-prompt
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
- `capture_method = "obs_scene_screenshot"`

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

Select the session folder created for the work session, then process the numbered JPEGs in order.
