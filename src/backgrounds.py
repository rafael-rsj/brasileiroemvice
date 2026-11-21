"""Cenários ilustrados originais no clima de Leonida, gerados por código (sem imagem de terceiros).

scene_svg(seed, w, h) devolve um SVG pronto para ir de fundo na arte quando a matéria não tem foto boa.
Cenas: praia, skyline, ponte, pantano, rodovia, marina. Paletas variam pelo seed.
"""
import math
import random

PALETTES = [
    # céu topo, céu meio, céu horizonte, sol A, sol B, água, silhueta, neon
    dict(name="sunset", s1="#1a0b3d", s2="#7a1f6e", s3="#ff6a5c", sun1="#ffe066", sun2="#ff4f7b", sea="#2b0f4c", sil="#12061f", neon="#ff3d9a"),
    dict(name="miami", s1="#0b1d3a", s2="#1f6f8b", s3="#ff9a8b", sun1="#fff3b0", sun2="#ff6f91", sea="#0f3d56", sil="#071527", neon="#22e1ff"),
    dict(name="night", s1="#05030f", s2="#1d0b3a", s3="#5b1a7a", sun1="#f4f1ff", sun2="#b9a7ff", sea="#0c0620", sil="#020108", neon="#b14cff"),
    dict(name="golden", s1="#2a1340", s2="#c4456c", s3="#ffb347", sun1="#fff1a8", sun2="#ff7b39", sea="#3a1a3f", sil="#1a0a17", neon="#ffcf4a"),
]

SCENES = ["praia", "skyline", "ponte", "pantano", "rodovia", "marina"]


def _defs(p, w, h):
    return f'''<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p['s1']}"/><stop offset=".55" stop-color="{p['s2']}"/><stop offset="1" stop-color="{p['s3']}"/></linearGradient>
<linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p['sun1']}"/><stop offset="1" stop-color="{p['sun2']}"/></linearGradient>
<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p['sea']}"/><stop offset="1" stop-color="{p['sil']}"/></linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{w/60:.0f}" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="soft"><feGaussianBlur stdDeviation="{w/240:.1f}"/></filter>
</defs>'''


def _stars(r, w, hz, n=90):
    out = []
    for _ in range(n):
        x, y = r.uniform(0, w), r.uniform(0, hz * 0.8)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.uniform(0.8, 2.6):.1f}" fill="#fff" opacity="{r.uniform(.25, .9):.2f}"/>')
    return "".join(out)


def _sun(p, cx, cy, rad, striped=True):
    stripes = ""
    if striped:
        for i in range(6):
            yy = cy + rad * (0.15 + i * 0.15)
            hh = rad * (0.03 + i * 0.012)
            stripes += f'<rect x="{cx-rad-5:.0f}" y="{yy:.0f}" width="{2*rad+10:.0f}" height="{hh:.0f}" fill="{p["s3"]}"/>'
    return f'<g filter="url(#glow)"><circle cx="{cx:.0f}" cy="{cy:.0f}" r="{rad:.0f}" fill="url(#sun)"/></g>{stripes}'


def _palm(x, base, hgt, lean, color, scale=1.0):
    tx, ty = x + lean, base - hgt
    trunk = (f'<path d="M{x-9*scale:.0f},{base} Q{x+lean*0.4:.0f},{base-hgt*0.5:.0f} {tx-4*scale:.0f},{ty:.0f} '
             f'L{tx+4*scale:.0f},{ty:.0f} Q{x+lean*0.4+14*scale:.0f},{base-hgt*0.5:.0f} {x+9*scale:.0f},{base} Z" fill="{color}"/>')
    leaves = ""
    for ang in (-160, -130, -100, -70, -40, -10, 20):
        a = math.radians(ang)
        L = 150 * scale
        ex, ey = tx + math.cos(a) * L, ty + math.sin(a) * L * 0.55 + 40 * scale
        mx, my = tx + math.cos(a) * L * 0.5, ty + math.sin(a) * L * 0.5 - 25 * scale
        leaves += (f'<path d="M{tx:.0f},{ty:.0f} Q{mx:.0f},{my:.0f} {ex:.0f},{ey:.0f} '
                   f'Q{mx+6*scale:.0f},{my+18*scale:.0f} {tx:.0f},{ty+8*scale:.0f} Z" fill="{color}"/>')
    return trunk + leaves


def _skyline(r, p, w, base, hmax, lit=True, color=None):
    color = color or p["sil"]
    out, x = [], -20
    while x < w + 20:
        bw = r.uniform(w * 0.04, w * 0.11)
        bh = r.uniform(hmax * 0.25, hmax)
        out.append(f'<rect x="{x:.0f}" y="{base-bh:.0f}" width="{bw:.0f}" height="{bh+2:.0f}" fill="{color}"/>')
        if r.random() < 0.25:  # antena
            out.append(f'<rect x="{x+bw/2-2:.0f}" y="{base-bh-bh*0.18:.0f}" width="4" height="{bh*0.18:.0f}" fill="{color}"/>')
        if lit:
            for wy in range(int(base - bh + 14), int(base - 10), 22):
                for wx in range(int(x + 8), int(x + bw - 10), 16):
                    if r.random() < 0.33:
                        c = r.choice(["#ffd27a", "#ffe9b0", p["neon"], "#9be7ff"])
                        out.append(f'<rect x="{wx}" y="{wy}" width="7" height="10" fill="{c}" opacity="{r.uniform(.45, .95):.2f}"/>')
        x += bw + r.uniform(2, 14)
    return "".join(out)


def _reflection(r, p, w, y0, h, color):
    out = []
    for i in range(14):
        yy = y0 + 18 + i * h / 16
        ww = r.uniform(w * 0.1, w * 0.45)
        out.append(f'<rect x="{w/2-ww/2:.0f}" y="{yy:.0f}" width="{ww:.0f}" height="{3 + i*0.4:.1f}" rx="2" fill="{color}" opacity="{0.55 - i*0.03:.2f}"/>')
    return "".join(out)


def scene_svg(seed: int, w: int = 1080, h: int = 1350, scene: str | None = None) -> str:
    r = random.Random(seed)
    p = PALETTES[seed % len(PALETTES)]
    scene = scene or SCENES[seed % len(SCENES)]
    hz = h * r.uniform(0.50, 0.58)  # linha do horizonte
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice">',
         _defs(p, w, h), f'<rect width="{w}" height="{h}" fill="url(#sky)"/>']
    night = p["name"] == "night"
    if night or scene in ("skyline", "pantano"):
        g.append(_stars(r, w, hz))

    if scene == "praia":
        g.append(_sun(p, w * r.uniform(.35, .65), hz - w * .05, w * .22))
        g.append(f'<rect y="{hz:.0f}" width="{w}" height="{h-hz:.0f}" fill="url(#sea)"/>')
        g.append(_reflection(r, p, w, hz, h * .25, p["sun2"]))
        g.append(f'<path d="M0,{h*.86:.0f} Q{w*.5:.0f},{h*.80:.0f} {w},{h*.88:.0f} L{w},{h} L0,{h} Z" fill="{p["sil"]}"/>')
        g.append(_palm(w * .12, h * .9, h * .5, w * .08, p["sil"], 1.3))
        g.append(_palm(w * .9, h * .92, h * .42, -w * .07, p["sil"], 1.1))
        g.append(_palm(w * .78, h * .9, h * .3, -w * .03, p["sil"], 0.8))

    elif scene == "skyline":
        g.append(f'<circle cx="{w*.8:.0f}" cy="{hz*.25:.0f}" r="{w*.06:.0f}" fill="{p["sun1"]}" filter="url(#glow)" opacity=".9"/>')
        g.append(_skyline(r, p, w, hz, h * .22, lit=False, color=p["s2"]))
        g.append(_skyline(r, p, w, hz + 4, h * .34, lit=True))
        g.append(f'<rect y="{hz:.0f}" width="{w}" height="{h-hz:.0f}" fill="url(#sea)"/>')
        for i in range(40):  # reflexo das luzes
            x = r.uniform(0, w)
            g.append(f'<rect x="{x:.0f}" y="{hz + r.uniform(10, (h-hz)*.6):.0f}" width="{r.uniform(10, 60):.0f}" height="3" fill="{r.choice([p["neon"], "#ffd27a"])}" opacity="{r.uniform(.2,.6):.2f}"/>')
        g.append(_palm(w * .06, h, h * .45, w * .05, p["sil"], 1.2))

    elif scene == "ponte":
        g.append(_sun(p, w * .5, hz - w * .02, w * .18))
        g.append(f'<rect y="{hz:.0f}" width="{w}" height="{h-hz:.0f}" fill="url(#sea)"/>')
        g.append(_reflection(r, p, w, hz, h * .3, p["sun2"]))
        deck = hz + h * .06
        g.append(f'<path d="M-10,{deck+30:.0f} Q{w*.5:.0f},{deck-30:.0f} {w+10},{deck+40:.0f} L{w+10},{deck+58:.0f} Q{w*.5:.0f},{deck-12:.0f} -10,{deck+48:.0f} Z" fill="{p["sil"]}"/>')
        for i in range(12):
            x = i * w / 11
            yt = deck + 30 - 60 * math.sin(math.pi * i / 11) * 0.5
            g.append(f'<rect x="{x-4:.0f}" y="{yt:.0f}" width="9" height="{h*.12:.0f}" fill="{p["sil"]}"/>')
        for i in range(6):  # faróis passando
            x = r.uniform(0, w)
            g.append(f'<circle cx="{x:.0f}" cy="{deck + 30 - 60*math.sin(math.pi*x/w)*0.5 + 4:.0f}" r="4" fill="#ffe9b0" filter="url(#glow)"/>')

    elif scene == "pantano":
        g.append(f'<circle cx="{w*.62:.0f}" cy="{hz*.45:.0f}" r="{w*.11:.0f}" fill="{p["sun1"]}" filter="url(#glow)"/>')
        g.append(f'<rect y="{hz:.0f}" width="{w}" height="{h-hz:.0f}" fill="url(#sea)"/>')
        g.append(_reflection(r, p, w, hz, h * .2, p["sun1"]))
        for _ in range(11):  # ciprestes e mangue: silhueta irregular, sem formas geométricas
            x = r.uniform(-40, w + 40)
            th = r.uniform(h * .16, h * .38)
            wd = th * r.uniform(.16, .26)
            pts_l, pts_r = [], []
            steps = 14
            for k in range(steps + 1):
                t = k / steps
                yy = hz + 6 - th * t
                half = wd * (1 - t) ** 0.7 * (0.55 + 0.45 * r.random())
                pts_l.append(f"{x - half - r.uniform(0, wd*.15):.0f},{yy:.0f}")
                pts_r.append(f"{x + half + r.uniform(0, wd*.15):.0f},{yy:.0f}")
            poly = " ".join(pts_l + pts_r[::-1])
            g.append(f'<polygon points="{poly}" fill="{p["sil"]}"/>')
            for k in range(5):  # musgo pendurado
                mx = x + r.uniform(-wd, wd) * .8
                my = hz - th * r.uniform(.25, .8)
                g.append(f'<path d="M{mx:.0f},{my:.0f} q{r.uniform(-6,6):.0f},{r.uniform(20,50):.0f} {r.uniform(-4,4):.0f},{r.uniform(40,90):.0f}" stroke="{p["sil"]}" stroke-width="{r.uniform(3,7):.0f}" fill="none" stroke-linecap="round"/>')
        g.append(f'<rect y="{hz-20:.0f}" width="{w}" height="80" fill="#fff" opacity=".10" filter="url(#soft)"/>')
        g.append(f'<path d="M0,{h*.9:.0f} Q{w*.3:.0f},{h*.86:.0f} {w*.6:.0f},{h*.92:.0f} T{w},{h*.9:.0f} L{w},{h} L0,{h} Z" fill="{p["sil"]}"/>')

    elif scene == "rodovia":
        g.append(_sun(p, w * .5, hz - w * .06, w * .2))
        g.append(f'<path d="M0,{hz:.0f} L{w*.18:.0f},{hz-h*.08:.0f} L{w*.32:.0f},{hz-h*.03:.0f} L{w*.5:.0f},{hz-h*.1:.0f} L{w*.7:.0f},{hz-h*.04:.0f} L{w*.85:.0f},{hz-h*.09:.0f} L{w},{hz-h*.02:.0f} L{w},{hz:.0f} Z" fill="{p["s2"]}" opacity=".9"/>')
        g.append(f'<rect y="{hz:.0f}" width="{w}" height="{h-hz:.0f}" fill="{p["sil"]}"/>')
        for i in range(1, 16):  # grade retrô
            t = i / 15
            yy = hz + (h - hz) * t * t
            g.append(f'<line x1="0" y1="{yy:.0f}" x2="{w}" y2="{yy:.0f}" stroke="{p["neon"]}" stroke-width="{1+t*3:.1f}" opacity="{.25+t*.4:.2f}"/>')
        for i in range(-8, 9):
            g.append(f'<line x1="{w/2 + i*w*0.02:.0f}" y1="{hz:.0f}" x2="{w/2 + i*w*0.25:.0f}" y2="{h}" stroke="{p["neon"]}" stroke-width="2" opacity=".45"/>')
        g.append(f'<path d="M{w*.47:.0f},{hz:.0f} L{w*.53:.0f},{hz:.0f} L{w*.8:.0f},{h} L{w*.2:.0f},{h} Z" fill="#0b0614"/>')
        for i in range(8):
            t0, t1 = i / 8, i / 8 + 0.05
            y0, y1 = hz + (h - hz) * t0 * t0, hz + (h - hz) * t1 * t1
            g.append(f'<path d="M{w/2-2-6*t0:.0f},{y0:.0f} L{w/2+2+6*t0:.0f},{y0:.0f} L{w/2+3+8*t1:.0f},{y1:.0f} L{w/2-3-8*t1:.0f},{y1:.0f} Z" fill="#ffe066"/>')
        g.append(_palm(w * .08, hz + h * .05, h * .35, w * .04, p["sil"], 1.0))
        g.append(_palm(w * .93, hz + h * .06, h * .32, -w * .04, p["sil"], 0.95))

    else:  # marina
        g.append(_sun(p, w * .3, hz - w * .03, w * .16, striped=False))
        g.append(_skyline(r, p, w, hz, h * .18, lit=True, color=p["s2"]))
        g.append(f'<rect y="{hz:.0f}" width="{w}" height="{h-hz:.0f}" fill="url(#sea)"/>')
        g.append(_reflection(r, p, w * 0.6, hz, h * .2, p["sun2"]))
        for i in range(5):  # barcos
            bx = w * (0.1 + i * 0.2) + r.uniform(-30, 30)
            by = hz + h * r.uniform(.08, .2)
            s = r.uniform(.7, 1.2)
            g.append(f'<path d="M{bx-60*s:.0f},{by:.0f} L{bx+70*s:.0f},{by:.0f} L{bx+50*s:.0f},{by+22*s:.0f} L{bx-45*s:.0f},{by+22*s:.0f} Z" fill="{p["sil"]}"/>')
            g.append(f'<rect x="{bx-2:.0f}" y="{by-130*s:.0f}" width="4" height="{130*s:.0f}" fill="{p["sil"]}"/>')
            g.append(f'<path d="M{bx+3:.0f},{by-125*s:.0f} L{bx+55*s:.0f},{by-10:.0f} L{bx+3:.0f},{by-10:.0f} Z" fill="{p["sil"]}" opacity=".85"/>')
        g.append(f'<rect y="{h*.9:.0f}" width="{w}" height="{h*.1:.0f}" fill="{p["sil"]}"/>')
        for i in range(14):
            g.append(f'<rect x="{i*w/13:.0f}" y="{h*.86:.0f}" width="10" height="{h*.06:.0f}" fill="{p["sil"]}"/>')

    # granulação leve
    g.append(f'<rect width="{w}" height="{h}" fill="{p["s1"]}" opacity=".08"/>')
    g.append("</svg>")
    return "".join(g)
