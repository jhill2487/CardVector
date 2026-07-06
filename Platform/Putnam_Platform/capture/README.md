# Putnam Capture v0.2

Checkpoint: OBS Capture Auto Crop Pipeline v0.1 is available as a post-capture
bridge for JPEGs produced by this module.

Putnam Capture captures still JPEGs from an OBS scene through OBS WebSocket.
OBS owns the camera/source stack; Putnam Capture saves whatever is visible in
the selected OBS scene.

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

The scene can contain any OBS source: DroidCam, iOS Camera, OBS Camera, webcam,
capture card, or another source.

## Settings

Putnam Capture reads and updates:

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
  "save_cropped_frame": false,
  "crop_rectangle": {
    "left": 0,
    "top": 0,
    "right": 0,
    "bottom": 0
  },
  "auto_capture_enabled": false,
  "auto_capture_min_delay_seconds": 2.0,
  "auto_capture_stable_seconds": 1.0,
  "thumbnail_preview": true
}
```

Crop settings are stored now, but live crop image output remains separate from capture. Full-frame JPEG capture remains the default, and `obs_capture_autocrop.py` can process the saved JPEGs after capture.

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

The launcher prompts for the OBS WebSocket password. On startup, Putnam Capture lists available OBS scenes. Press Enter to use the configured default scene, or type another scene name exactly as it appears in OBS.

Optional examples:

```bat
Run_Putnam_Capture.bat --scene "03 - Card Capture" --no-scene-prompt
Run_Putnam_Capture.bat --mode front --batch-name "June 28 intake"
Run_Putnam_Capture.bat --auto-capture
Run_Putnam_Capture.bat --no-preview
```

## Capture Modes

Choose one startup mode:

- Front only
- Back only
- Front/back pairs

Filenames:

```text
000001_front.jpg
000001_back.jpg
000002_front.jpg
```

The console shows the next expected file, for example:

```text
Next: 000004_back.jpg
```

## Controls

- Spacebar: manual capture.
- U: undo the last capture.
- A: toggle auto-capture on/off.
- Q: close the app.
- Escape: close the app.

Manual Space capture always works, even when auto-capture is off or on.

Undo moves the last active capture into the session `undone` folder instead of deleting it.

## Preview

When practical, Putnam Capture opens a small thumbnail window showing the last captured JPEG. Use `--no-preview` to disable it.

## Auto-Capture

Auto-capture is off by default. When enabled, Putnam Capture checks for a stable OBS scene frame and respects a minimum delay between captures. It is intended as an assist, not a replacement for manual capture.

Use `A` during a session to toggle auto-capture.

## Output

Each run creates a new session folder:

```text
<root>\Putnam_OS\Incoming Files\Capture_Sessions\<YYYY-MM-DD_HHMMSS>_<batch_name>\
```

Images are saved to:

```text
<session>\images\000001_front.jpg
<session>\images\000001_back.jpg
<session>\images\000002_front.jpg
```

The session folder is printed during capture and opens automatically when the session finishes.

The app also writes:

- `session.json`
- `capture_log.csv`

`session.json` includes:

- `batch_name`
- `mode`
- `image_count`
- `front_count`
- `back_count`
- `obs_scene`
- `output_folder`
- `capture_method = "obs_scene_screenshot"`

`capture_log.csv` includes:

- `filename`
- `timestamp`
- `side`
- `card_number`
- `obs_scene`
- `status`

## Import Into CardUploader

After capture, open CardUploader and import from the printed `images` folder:

```text
<root>\Putnam_OS\Incoming Files\Capture_Sessions\<YYYY-MM-DD_HHMMSS>_<batch_name>\images
```

Process the numbered JPEGs in order.

## Putnam OS Inventory Audit Integration

Putnam OS Inventory Audit Mode can launch Capture Studio as an optional
internal verification-image source.

This use is evidence-only:

- No OCR.
- No scanner identification.
- No CardUploader recognition.
- No eBay image upload.

When enabled in Putnam OS, confirmed audit cards copy the latest Capture Studio
JPEG into:

```text
%USERENVIRONMENT%\Putnam_OS\System\data\inventory_audit\audit_images\
```

The operator still confirms the listing/card manually. Capture Studio is only
helping record proof that the physical card was checked.

## OBS Capture Auto Crop Pipeline v0.1

The auto crop pipeline processes JPEGs saved by Putnam Capture and writes
standard card crops for scanner, overlay, or Putnam OS consumers.

Run against a capture session image folder:

```bat
%USERENVIRONMENT%\Putnam_Platform\tools\Run_OBS_AutoCrop.bat --input "%USERENVIRONMENT%\Putnam_OS\Incoming Files\Capture_Sessions\<session>\images" --output "%USERENVIRONMENT%\processed\obs_autocrop" --debug
```

Or run the Python module directly from the project root:

```bat
python Putnam_Platform\capture\obs_capture_autocrop.py --input "Putnam_OS\Incoming Files\Capture_Sessions\<session>\images" --output "processed\obs_autocrop" --debug
```

Outputs:

```text
processed\obs_autocrop\<source>_card.jpg
processed\obs_autocrop\<source>_debug.jpg
processed\obs_autocrop\<source>_metadata.json
```

Metadata status values:

- `cropped`: clean quadrilateral detected and perspective-corrected.
- `fallback_crop`: likely card rectangle found, using bounding rectangle fallback.
- `no_card_found`: no suitable card contour found.
- `error`: image read/write or processing failed.

Watch mode is optional:

```bat
python Putnam_Platform\capture\obs_capture_autocrop.py --input "captures" --output "processed\obs_autocrop" --watch --debug
```

If `watchdog` is not installed, watch mode prints an install command and exits
cleanly. Batch mode does not require `watchdog`.

Scanner/overlay integration point:

```python
identify_card_from_crop(cropped_path)
```

The function is intentionally a TODO hook until the active scanner/overlay
callable interface is clear. This keeps v0.1 focused on the capture-to-crop
bridge instead of becoming a scanner rewrite.

Smoke test:

1. Capture or select one normal OBS JPEG with one card.
2. If available, include one rotated/upside-down card capture.
3. Include one JPEG with no obvious card.
4. Run the pipeline with `--debug`.
5. Verify card/debug/metadata files are created for crop candidates.
6. Verify no-card images write metadata with `status = "no_card_found"` and do not crash.
