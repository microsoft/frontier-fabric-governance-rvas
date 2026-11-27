# Icon requirements

The agent package needs two PNG icons, and the
[Agent build](../../.github/workflows/agent-build.yml) workflow packages the
ones in this folder:

- `color.png`: 192×192 pixels, full color.
- `outline.png`: 32×32 pixels, white lines on a transparent background.

Both are required by the Teams app manifest, and Microsoft 365 rejects the
package if either is missing or has the wrong dimensions. To replace an icon,
keep its file name and size; the
[icon guidelines](https://learn.microsoft.com/microsoftteams/platform/concepts/design/design-teams-app-icon-store-appbar)
cover the safe area and contrast.

To recreate the placeholder icons with ImageMagick:

```bash
convert -size 192x192 xc:'#2A6DF4' agent/appPackage/color.png
convert -size 32x32 xc:none -fill white -draw "circle 16,16 16,4" agent/appPackage/outline.png
```
