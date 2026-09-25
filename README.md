# magnify-glass

A physically-simulated magnifying glass for your screen: real optics, not just scaling.

A round, frameless, always-on-top lens floats over your desktop and refracts whatever is underneath it. You set the glass's refractive index, curvature, thickness and height above the screen. The lens then works out its focal length and magnification from the lensmaker's equation, so you get barrel and pincushion distortion, image inversion past the focal point, chromatic fringing and soft edges.

![Lens interface with parameter icons](ui_interface.png)

*Parameter icons appear around the rim when you hover near the edge. This lens has high curvature and sits past its focal point, so the image is inverted (-0.3x).*

![Zoomed-out lens with strong distortion](ui_zoomed_out.png)

*A strongly curved lens at 0.8x, showing heavy barrel distortion and chromatic aberration.*

## Features

- **Real lens math:** focal length comes from the lensmaker's equation for a symmetric biconvex (or biconcave) lens. Magnification comes from the lens height above the screen.
- **Radial distortion:** barrel and pincushion warping that scales with refractive index and curvature.
- **Chromatic aberration:** red and blue channels shift radially, like cheap glass.
- **Edge blur:** progressive softening toward the rim.
- **8 presets:** Reading, Loupe, Paperweight, Fish-eye, Flat, Peephole, Spoon, Globe.
- **Floating window:** round, draggable, resizable (120–800 px) and always on top.
- **Screenshot mode:** freeze the lens so it shows up in screenshots (see below).

## Requirements

- Windows (the round window, click-through region and capture exclusion use Win32 APIs)
- Python 3.8+

```
pip install pygame mss numpy
```

## Usage

```
python magnifier.py
```

### Controls

| Action | How |
|---|---|
| Move the lens | Click and drag anywhere inside it |
| Show parameter icons | Hover near the rim |
| Adjust a parameter | Scroll over its icon, or click-drag the icon (left/right or up/down) |
| Adjust the selected parameter | Scroll anywhere on the lens |
| Select a parameter | Click its icon, or press `1`–`7` |
| Presets / pin / close | Hover the bottom of the lens to show the HUD |
| Resize | Drag the handle at the bottom-right of the HUD |
| Screenshot mode | `F9` (global, works without focus) |
| Quit | `Esc` or the red X in the HUD |

### Parameters

| # | Icon | Parameter | Range | Effect |
|---|---|---|---|---|
| 1 | Prism | **n**: refractive index | 1.0 – 3.0 | Stronger bending, shorter focal length |
| 2 | Arcs | **C**: curvature (1/R) | -20 – 20 | Positive = convex (magnifies), negative = concave (shrinks) |
| 3 | Bars | **d**: thickness | 0 – 1 | Thick-lens correction to focal length |
| 4 | Arrow | **H**: height above screen | 0.01 – 5 | Near the focal point magnification spikes; past it the image flips |
| 5 | Magnifier | **Z**: zoom | 0.2 – 5 | Extra digital zoom on top of the optics |
| 6 | RGB rings | **CA**: chromatic aberration | 0 – 2 | Color fringing toward the edge |
| 7 | Rings | **EB**: edge blur | 0 – 1 | Softness toward the rim |

The live magnification is shown at the bottom of the lens. A negative value means the image is inverted.

## Taking screenshots of the lens

The lens hides itself from all screen capture (`WDA_EXCLUDEFROMCAPTURE`) so that it doesn't magnify its own window. That also hides it from the Snipping Tool and other screenshot apps.

To capture it:

1. Put the lens where you want it.
2. Press **F9**. The lens freezes on its current image and becomes visible to capture.
3. Take your screenshot (e.g. **Win+Shift+S**).
4. Press **F9** again to go back to the live lens.

On some laptops you may need **Fn+F9**.

## License

MIT, see [LICENSE](LICENSE).
