"""Bonequinhos simples (ela, ele, mãe, amigo) que aparecem com balão de fala nos carrosséis do Tio Vice."""

SKIN = "#e0a47a"
LINE = "#1a1024"


def _face(cx, cy, r=62, lash=False, glasses=False, beard=False):
    eyes = (f'<path d="M{cx-26} {cy-4} q8 -10 16 0" stroke="{LINE}" stroke-width="5" fill="none" stroke-linecap="round"/>'
            f'<path d="M{cx+10} {cy-4} q8 -10 16 0" stroke="{LINE}" stroke-width="5" fill="none" stroke-linecap="round"/>')
    if lash:
        eyes += (f'<path d="M{cx-28} {cy-8} l-6 -5 M{cx+28} {cy-8} l6 -5" stroke="{LINE}" stroke-width="4" stroke-linecap="round"/>')
    cheeks = (f'<circle cx="{cx-34}" cy="{cy+14}" r="9" fill="#ff8fab" opacity=".55"/>'
              f'<circle cx="{cx+34}" cy="{cy+14}" r="9" fill="#ff8fab" opacity=".55"/>')
    mouth = f'<path d="M{cx-18} {cy+18} q18 20 36 0" stroke="{LINE}" stroke-width="5" fill="#fff" stroke-linejoin="round"/>'
    extra = ""
    if glasses:
        extra += (f'<g fill="none" stroke="{LINE}" stroke-width="4"><circle cx="{cx-18}" cy="{cy-4}" r="15"/>'
                  f'<circle cx="{cx+18}" cy="{cy-4}" r="15"/><path d="M{cx-3} {cy-4}h6"/></g>')
    if beard:
        extra += f'<path d="M{cx-50} {cy+6} q4 56 50 58 q46 -2 50 -58 q-10 26 -50 28 q-40 -2 -50 -28z" fill="#5a3a24"/>'
        mouth = f'<path d="M{cx-14} {cy+24} q14 14 28 0" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round"/>'
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{SKIN}" stroke="{LINE}" stroke-width="5"/>'
            + cheeks + eyes + extra + mouth)


def boneco(quem: str, width: int = 240) -> str:
    """SVG de um personagem sorrindo, da cintura pra cima. quem: ela | ele | mae | amigo."""
    cx, cy = 120, 110
    if quem == "ela":
        back = f'<path d="M48 110 q-6 -92 72 -92 q78 0 72 92 l10 120 h-164z" fill="#3b2314" stroke="{LINE}" stroke-width="5"/>'
        body = f'<path d="M30 300 q0 -132 90 -132 q90 0 90 132z" fill="#ff5fa2" stroke="{LINE}" stroke-width="5"/>'
        front = (f'<path d="M58 96 q20 -66 98 -50 q30 10 30 50 q-50 -6 -76 -36 q-20 30 -52 36z" fill="#3b2314"/>'
                 f'<circle cx="168" cy="58" r="12" fill="#ffc145" stroke="{LINE}" stroke-width="4"/>')
        face = _face(cx, cy, lash=True)
    elif quem == "mae":
        back = f'<circle cx="120" cy="34" r="30" fill="#8a8a8a" stroke="{LINE}" stroke-width="5"/>'
        body = (f'<path d="M30 300 q0 -132 90 -132 q90 0 90 132z" fill="#7b61ff" stroke="{LINE}" stroke-width="5"/>'
                f'<path d="M84 210 h72 v90 h-72z" fill="#fff" stroke="{LINE}" stroke-width="4"/>')
        front = f'<path d="M58 100 q4 -64 62 -64 q58 0 62 64 q-30 -30 -62 -30 q-32 0 -62 30z" fill="#9a9a9a"/>'
        face = _face(cx, cy, glasses=True)
    elif quem == "amigo":
        back = ""
        body = f'<path d="M30 300 q0 -132 90 -132 q90 0 90 132z" fill="#00b3c7" stroke="{LINE}" stroke-width="5"/>'
        front = (f'<path d="M60 92 q8 -58 60 -58 q52 0 60 58 q-26 -18 -60 -18 q-34 0 -60 18z" fill="#2b1a10"/>'
                 f'<path d="M50 112 q0 -82 70 -82 q70 0 70 82" fill="none" stroke="{LINE}" stroke-width="9"/>'
                 f'<rect x="38" y="100" width="22" height="40" rx="8" fill="#ff3d7f" stroke="{LINE}" stroke-width="4"/>'
                 f'<rect x="180" y="100" width="22" height="40" rx="8" fill="#ff3d7f" stroke="{LINE}" stroke-width="4"/>'
                 f'<path d="M50 134 q10 40 44 40" fill="none" stroke="{LINE}" stroke-width="4"/>')
        face = _face(cx, cy)
    else:  # ele
        back = ""
        body = f'<path d="M30 300 q0 -132 90 -132 q90 0 90 132z" fill="#3a6df0" stroke="{LINE}" stroke-width="5"/>'
        front = f'<path d="M58 96 q6 -64 62 -64 q56 0 62 64 q-18 -26 -62 -26 q-44 0 -62 26z" fill="#2b1a10"/>'
        face = _face(cx, cy, beard=True)
    h = int(width * 300 / 240)
    return (f'<svg width="{width}" height="{h}" viewBox="0 0 240 300" xmlns="http://www.w3.org/2000/svg">'
            f'{back}{body}{face}{front}</svg>')
