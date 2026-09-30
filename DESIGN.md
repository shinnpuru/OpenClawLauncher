# OpenClaw Launcher website

An independent product introduction inspired by the clarity and restraint of OpenAI's website. The launcher retains its own name, logo and product identity.

## Visual system

- White canvas, near-black text (`#171717`), secondary gray (`#676767`), fine dividers (`#e6e6e6`).
- System sans-serif fonts with native Chinese fallbacks. No remote fonts or dependencies.
- Large, medium-weight headings; generous whitespace; concise, concrete Chinese copy.
- Pill buttons for actions and preview tabs. Minimal framing, with a neutral stage for product screenshots.
- Six capabilities on a simple three-column grid, three setup steps and common questions. Download buttons link directly to the latest release page.
- Responsive desktop, tablet and phone layouts. Visible focus, keyboard-operable tabs, native disclosures and dialog, and reduced-motion support.

## Content and maintenance

`index.html`, `styles.css` and `script.js` are static files served from the root of `gh-pages`. Keep `CNAME` intact. Download links use `releases/latest` so they remain valid when release filenames change; labels make the destination explicit.

Screenshots were rendered from the current main-branch launcher widgets (commit `05022d6`, 2026-09-30), in an isolated temporary workspace with empty demo configuration. They contain no credentials, personal paths or user data. The home screenshot shows the real first-run state; other panels use an empty demo instance. No runtime installation or model service is started.

Refresh screenshots with the launcher's Python environment:

```sh
/path/to/main-checkout/.venv/bin/python scripts/capture_screenshots.py /path/to/main-checkout
```

The script renders all 11 panels at 2× scale using Qt's offscreen platform and waits for sidebar animation to settle. Verify the generated images before publishing. Six panels appear in the interactive showcase; remaining images are retained as current documentation assets.

Preview the site with `python3 -m http.server 8765 --bind 127.0.0.1`. Check screenshot switching, keyboard navigation, image enlargement and dismissal, FAQ disclosures, section anchors, mobile overflow and download destinations before updating `gh-pages`.
