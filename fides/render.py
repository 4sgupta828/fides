"""fides.render — turn a VERIFIED spec into actual pixels, with zero dependencies. SVG is text, so a
grounded infographic renders to a real .svg file (openable, embeddable, convertible to PNG by any
consumer) without pulling a canvas/ffmpeg dep into the core. The storyboard renders to a self-contained
HTML that plays the scenes as timed frames — a preview any browser runs, no ffmpeg required.

The invariant that makes this safe: a renderer draws ONLY what is in the spec, and the spec only ever
contains figures the Gate verified (studio builds it that way). So there is NO path from renderer to an
un-grounded number — you cannot render a stat the ledger did not pass. render_asset() enforces it
belt-and-suspenders: it refuses an un-shippable GroundedAsset unless you explicitly opt in.
"""
from __future__ import annotations
from typing import Optional

# ---- primitives ---------------------------------------------------------------------------------
_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}


def _esc(s) -> str:
    return "".join(_ESC.get(c, c) for c in str(s))


_BG, _FG, _ACCENT, _MUTED = "#0f172a", "#f8fafc", "#38bdf8", "#94a3b8"


# ---- infographic spec -> SVG --------------------------------------------------------------------
def infographic_svg(spec: dict, width: int = 1080, accent: str = _ACCENT) -> str:
    """A grounded {kind:'infographic', title, stats:[{value,label}]} → one poster-style SVG string."""
    stats = spec.get("stats", [])
    pad, title_h, card_h, gap = 64, 132, 150, 24
    height = title_h + (card_h + gap) * len(stats) + pad
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif">' % (width, height, width, height),
           '<rect width="%d" height="%d" fill="%s"/>' % (width, height, _BG),
           '<text x="%d" y="%d" fill="%s" font-size="46" font-weight="700">%s</text>'
           % (pad, 84, _FG, _esc(spec.get("title", ""))),
           '<rect x="%d" y="%d" width="72" height="6" rx="3" fill="%s"/>' % (pad, 104, accent)]
    y = title_h
    for s in stats:
        out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="18" fill="#1e293b"/>'
                    % (pad, y, width - 2 * pad, card_h))
        out.append('<text x="%d" y="%d" fill="%s" font-size="76" font-weight="800">%s</text>'
                    % (pad + 36, y + 92, accent, _esc(s["value"])))
        out.append('<text x="%d" y="%d" fill="%s" font-size="30" letter-spacing="1">%s</text>'
                    % (pad + 36, y + 130, _MUTED, _esc(s["label"]).upper()))
        y += card_h + gap
    out.append('</svg>')
    return "\n".join(out)


# ---- storyboard spec -> self-contained HTML player ----------------------------------------------
def _scene_svg(sc: dict, width: int, height: int, accent: str) -> str:
    body = []
    if sc.get("visual") == "title" or sc.get("title"):
        body.append('<text x="50%%" y="50%%" fill="%s" font-size="64" font-weight="800" '
                    'text-anchor="middle" dominant-baseline="middle">%s</text>' % (_FG, _esc(sc.get("title", ""))))
    else:
        body.append('<text x="50%%" y="44%%" fill="%s" font-size="120" font-weight="800" '
                    'text-anchor="middle" dominant-baseline="middle">%s</text>' % (accent, _esc(sc.get("value", ""))))
        body.append('<text x="50%%" y="60%%" fill="%s" font-size="32" letter-spacing="2" '
                    'text-anchor="middle">%s</text>' % (_MUTED, _esc(sc.get("label", "")).upper()))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'font-family="Inter,Segoe UI,Helvetica,Arial,sans-serif"><rect width="%d" height="%d" fill="%s"/>%s</svg>'
            % (width, height, width, height, width, height, _BG, "".join(body)))


def storyboard_html(spec: dict, width: int = 960, height: int = 540, seconds_per_scene: float = 2.5,
                    accent: str = _ACCENT) -> str:
    """A grounded {kind:'storyboard', scenes:[...]} → a self-contained HTML that plays each scene as a
    timed frame (CSS keyframes, no JS, no ffmpeg). Every frame is one verified stat."""
    scenes = spec.get("scenes", [])
    n = max(1, len(scenes))
    total = n * seconds_per_scene
    frames = "".join('<div class="f">%s</div>' % _scene_svg(sc, width, height, accent) for sc in scenes)
    # each frame visible for its slice, then hidden — a simple cross-cut
    step = 100.0 / n
    keyframes = []
    for i in range(n):
        a, b = i * step, (i + 1) * step
        kf = "@keyframes s%d{0%%,%.3f%%{opacity:0}%.3f%%,%.3f%%{opacity:1}%.3f%%,100%%{opacity:0}}" % (
            i, max(0, a - 0.01), a, max(a, b - 0.01), b if b < 100 else 100)
        keyframes.append(kf)
    css_rules = "".join(".f:nth-child(%d){animation:s%d %.2fs infinite}" % (i + 1, i, total) for i in range(n))
    return ("<!doctype html><meta charset=utf-8><title>%s</title>"
            "<style>body{margin:0;background:#000;display:grid;place-items:center;height:100vh}"
            ".stage{position:relative;width:%dpx;height:%dpx}"
            ".f{position:absolute;inset:0;opacity:0}%s %s</style>"
            "<div class=stage>%s</div>" % (_esc(spec.get("title", "")), width, height,
                                           "".join(keyframes), css_rules, frames))


# ---- asset-level entry (grounding-preserving) ---------------------------------------------------
def render_asset(asset, allow_unshippable: bool = False, **kw) -> str:
    """Render a studio GroundedAsset to SVG (image) or HTML (video). Refuses an un-shippable asset
    unless allow_unshippable=True — you cannot accidentally render a withheld/fabricated figure."""
    if not asset.shippable and not allow_unshippable:
        raise ValueError("refusing to render un-shippable asset %s (withheld: %s); pass allow_unshippable=True to override"
                         % (asset.id, asset.withheld))
    if asset.format == "image":
        return infographic_svg(asset.spec, **kw)
    if asset.format == "video":
        return storyboard_html(asset.spec, **kw)
    raise ValueError("no renderer for format %r (post is text: use asset.spec['text'])" % asset.format)
