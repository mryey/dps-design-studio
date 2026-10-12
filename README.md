# DPS Design Studio — Foundation 0.3

A native, local Windows-oriented apparel artwork editor. No account, server, subscription, network requests, or API keys in the editor. Internet is needed once to download Python and build dependencies.

## What this release includes

PNG/JPG import; editable image and text layers; dragging; layer ordering, visibility, locking and opacity; resize in inches; rotation and flips; canvas crop; undo/redo; editable `.dps` projects; transparent PNG export with DPI metadata and full pixel dimensions. Text supports color, size and an optional local TTF/OTF font file. Use licensed fonts. Text is rasterized for rendering; its text settings remain editable in the project.

## Warp text

Select an unlocked text layer and click **Warp text**. Choose **Arc**, **Arch**, **Wave**, or **Bulge**, adjust **Bend** from -100 to 100, review the preview and click **Apply**. Use zero bend or Reset to remove the warp. Cancel leaves the project unchanged. Text settings and warp settings remain editable, survive saving and reopening, and support undo/redo.

Arc bends the baseline and rotates the letters around a circular path. Arch vertically deforms the text into an arch. Wave produces a wave deformation. Bulge stretches/compresses text height around the center. Negative bend reverses each effect. Tall text automatically limits the Arc angle to avoid folding. These presets do not duplicate Adobe algorithms; no freeform mesh, horizontal/vertical distortion sliders, or vertical orientation control is included yet.

Warp expands the rendered bounds around the layer center. Width/height fields show dimensions **before warp**; position the text inside the canvas to avoid clipping and check exported artwork before printing. Preview renders at reduced resolution.

## Color adjustments

Select an unlocked layer and click **Adjustments**. Enable the tools you need, change their settings, review the combined preview, then click **Apply**. Cancel leaves the project untouched. Changes can be undone and are retained in `.dps` projects. Original image pixels and transparency are preserved.

- **Curves:** master RGB plus individual R/G/B channels. Click to add/update points, right-click to remove interior points, or type coordinate pairs. Points are connected with straight segments, not smooth Photoshop-style splines.
- **Levels:** input black/white, midtone gamma, output black/white.
- **Hue/Saturation:** hue shift from -180 to 180 degrees and saturation from -100 to 100 percent; no color-range targeting or lightness control yet.
- **Invert:** invert RGB without changing alpha.
- **Threshold:** black/white luminance cutoff from 0 to 255.
- **Gradient Map:** two selectable colors, from shadows to highlights; multiple gradient stops are not yet supported.

Combined tools run in this fixed order: Curves, Levels, Hue/Saturation, Invert, Threshold, Gradient Map. Settings apply to the selected layer, not an independent adjustment layer or mask. Reduced previews may differ at fine edges from full-resolution exports.

To update an existing installation, close DPS Design Studio, extract this updated package into a new folder and rerun **Setup-Windows.cmd**. Your separately saved projects remain in their chosen locations. Older foundation projects open without adjustment settings.

## Step-by-step Windows setup

1. Download this ZIP. Right-click it and choose **Extract All**. Open the extracted `dps-design-studio` folder. Do not run setup from inside the ZIP.
2. Install **Python 3.12, Windows installer (64-bit)** from the official release page: https://www.python.org/downloads/release/python-31210/ . Use the Windows installer, not the source archive. Keep the Python launcher and Tcl/Tk options enabled. Python is only a build tool; the bundled application will not need a separate Python installation.
3. Double-click **Setup-Windows.cmd**. It creates an isolated environment, downloads Pillow and PyInstaller, runs engine tests, builds the Windows application, copies it into your user's LocalAppData folder and creates a desktop shortcut. No administrator rights are intended to be required. Allow setup to finish; keep any error message for troubleshooting.
4. Launch **DPS Design Studio** from your desktop shortcut. After installation the editor works offline.
5. Click **Import image**, choose a PNG or JPG, and drag it into position.
6. Select a layer. Set width/height in inches and click **Apply layer changes**. Enter both dimensions proportionally to avoid distortion. X/Y are pixels; positive rotation is counterclockwise.
7. Click **Add text**, enter text, font size and color. You may choose a local `.ttf` or `.otf` file. If no font is selected, the bundled basic font is used.
8. Click **Save** and choose a project location such as `Documents\DPS Projects`. The `.dps` file embeds artwork and text settings. Keep your source artwork too. A custom font file is not embedded; reopening shows saved text correctly, but editing that text needs its original font or a replacement.
9. Click **Export PNG** for the print image. The checkerboard and selection outline are not exported. Pixels outside the canvas and hidden layers are excluded. Check the file with your transfer supplier before production.
10. Reopen the `.dps` project to continue editing. Use Ctrl+S, Ctrl+O, Ctrl+Z and Ctrl+Y outside text fields.

If setup reports `py` or Python 3.12 missing, repair/install Python 3.12 with the launcher enabled, then rerun setup. If PowerShell policy prevents the installer script from running, keep the error and ask for assistance; this package does not change execution policy. The built app can still be launched from `dist\DPS Design Studio\DPS Design Studio.exe`, keeping its entire surrounding folder together.

## First order acceptance check

Use a copy of your artwork. Create a 12 × 14 inch canvas at 300 DPI, import transparent artwork, add text, duplicate a layer, hide the duplicate, rotate/flip the original, and undo/redo. Save, close, reopen and verify the artwork visually. Export and confirm 3600 × 4200 pixels, transparency and expected placement. Verify crop on a separate project and confirm locked layers cannot be dragged. These Windows/UI checks have not yet been run by the author in the available environment.

## Limits and next stages

This is the foundation release, not the complete planned tool list or a complete Photoshop replacement. It does not yet include layer groups, masks, brushes, erasing, selection tools, background removal, effects, blend modes, PSD support, gang-sheet automation or realistic mockup warping. Basic text and rotation are included; skew and perspective distortion are not.

There is a 40-million-pixel canvas/layer limit, 100-layer limit, 100 MB project-file limit and 12-step undo history. Large images and history consume memory. The 22 × 120 inch sheet at 300 DPI requires 6600 × 36000 = 237,600,000 pixels; this release deliberately rejects it. A memory-efficient tiled gang-sheet engine is needed in a later release. Source resolution checks describe pixel density, not sharpness or guaranteed print quality. This release exports RGB/RGBA PNG; no CMYK conversion or ICC color-management workflow is implemented.

## Developer commands

From this folder:

```text
python -m pip install -r requirements.txt
python app.py
python -m unittest discover -s tests -v
```

Build on Windows using `Setup-Windows.cmd`. PyInstaller bundles for the active operating system; this Linux environment cannot generate a verified Windows executable. The package provides source and build/install scripts, not a prebuilt installer.

To uninstall, close the app, remove the desktop shortcut and delete `%LOCALAPPDATA%\DPSDesignStudio`. Your separately saved projects remain in their chosen locations.

## Verification record

Python 3.12 / Pillow 12.3.0: 32 engine tests passed, covering PNG size/transparency/DPI and layer order, project round-trip, history, hidden layers/opacity, crop, flip, embedded text rendering, invalid-save preservation, canvas limits, rotation and clipping. Source compilation passed. 14 new adjustment tests also verify formulas, RGB channel controls, hue and saturation, unchanged alpha and source pixels, adjustment persistence/export/undo, execution order, invalid settings, and older-project compatibility. Eight warp tests additionally cover identity, both bend directions, shape changes, source preservation, transparent borders, tall-text arc behavior, text editing, project/export round-trip, history and settings validation. A rendered preset comparison was visually inspected. Native window launch was attempted but blocked because this environment has no display. Windows build/install and UI interaction are unverified.

## Technical references

- Tkinter: https://docs.python.org/3/library/tkinter.html
- Pillow image operations: https://pillow.readthedocs.io/en/stable/reference/Image.html
- PyInstaller platform-specific builds: https://pyinstaller.org/en/stable/operating-mode.html
- PyInstaller commands: https://pyinstaller.org/en/stable/usage.html

Source was generated for Diamond Print Shop. Third-party dependencies retain their own licenses.
