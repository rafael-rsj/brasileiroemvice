"""Tio Vice: mascote original da página (ilustração vetorial feita em código).

Coroa brasileiro, sem camisa, definido e tatuado, barba grisalha cheia,
boné com as cores do pôr do sol de Vice City e um controle branco genérico na mão.
mascot_svg(expr) devolve um <svg> pronto para colocar nas artes.
expr: "sorriso" | "piscada" | "surpreso"
"""

OUT = "#2b1a12"     # contorno
SKIN = "#e8a472"
SKIN_SH = "#c97f4f"
SKIN_HI = "#f6c39b"
BEARD = "#e9e6e1"
BEARD_SH = "#bdb7ae"
INK = "#1f4f5c"     # tatuagem


def mascot_svg(expr: str = "sorriso", width: int = 620) -> str:
    h = int(width * 760 / 600)
    eyes = {
        "sorriso": f'''<path d="M246 252 q14 -12 28 0" stroke="{OUT}" stroke-width="6" fill="none" stroke-linecap="round"/>
                       <path d="M326 252 q14 -12 28 0" stroke="{OUT}" stroke-width="6" fill="none" stroke-linecap="round"/>''',
        "piscada": f'''<ellipse cx="260" cy="250" rx="9" ry="11" fill="{OUT}"/><circle cx="263" cy="246" r="3" fill="#fff"/>
                       <path d="M326 252 q14 -12 28 0" stroke="{OUT}" stroke-width="6" fill="none" stroke-linecap="round"/>''',
        "surpreso": f'''<ellipse cx="260" cy="248" rx="10" ry="13" fill="{OUT}"/><circle cx="263" cy="243" r="3.5" fill="#fff"/>
                        <ellipse cx="340" cy="248" rx="10" ry="13" fill="{OUT}"/><circle cx="343" cy="243" r="3.5" fill="#fff"/>''',
    }[expr]
    mouth = {
        "sorriso": f'''<path d="M262 318 q38 34 76 0 q-38 14 -76 0 z" fill="#7a2b2b" stroke="{OUT}" stroke-width="4"/>
                       <path d="M270 322 q30 10 60 0 l-4 8 q-26 7 -52 0 z" fill="#fff"/>''',
        "piscada": f'''<path d="M266 318 q40 30 74 -4" stroke="{OUT}" stroke-width="6" fill="none" stroke-linecap="round"/>''',
        "surpreso": f'''<ellipse cx="300" cy="328" rx="16" ry="20" fill="#7a2b2b" stroke="{OUT}" stroke-width="4"/>''',
    }[expr]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 760" width="{width}" height="{h}">
<defs>
  <linearGradient id="cap" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#ff3d7f"/><stop offset=".55" stop-color="#ff8a3d"/><stop offset="1" stop-color="#ffc145"/>
  </linearGradient>
  <linearGradient id="brim" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#6a1b6e"/><stop offset="1" stop-color="#2a0f4c"/>
  </linearGradient>
  <linearGradient id="torso" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{SKIN_SH}"/><stop offset=".25" stop-color="{SKIN}"/><stop offset=".7" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_SH}"/>
  </linearGradient>
</defs>
<g stroke-linejoin="round" stroke-linecap="round">
  <!-- tronco -->
  <path d="M70 760 C70 560 110 470 200 430 L400 430 C490 470 530 560 530 760 Z" fill="url(#torso)" stroke="{OUT}" stroke-width="7"/>
  <!-- trapézio / pescoço -->
  <path d="M235 380 L235 440 C265 470 335 470 365 440 L365 380 Z" fill="{SKIN_SH}" stroke="{OUT}" stroke-width="6"/>
  <!-- peitoral -->
  <path d="M150 520 C190 485 270 480 296 505 C300 560 260 590 200 585 C165 580 145 555 150 520 Z" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/>
  <path d="M450 520 C410 485 330 480 304 505 C300 560 340 590 400 585 C435 580 455 555 450 520 Z" fill="{SKIN}" stroke="{OUT}" stroke-width="5"/>
  <path d="M175 545 q40 -30 95 -22" stroke="{SKIN_HI}" stroke-width="8" fill="none" opacity=".8"/>
  <path d="M425 545 q-40 -30 -95 -22" stroke="{SKIN_HI}" stroke-width="8" fill="none" opacity=".8"/>
  <!-- abdômen -->
  <g stroke="{SKIN_SH}" stroke-width="6" fill="none">
    <path d="M300 600 L300 760"/><path d="M240 640 q60 14 120 0"/><path d="M245 700 q55 12 110 0"/>
  </g>
  <!-- tatuagem no peito: estrela e onda -->
  <g stroke="{INK}" stroke-width="5" fill="none">
    <path d="M190 470 l9 18 20 3 -15 14 4 20 -18 -10 -18 10 4 -20 -15 -14 20 -3 z"/>
  </g>
  <!-- braço esquerdo (do personagem à direita da tela) -->
  <path d="M470 470 C540 500 560 580 530 640 C510 680 460 690 420 670 L380 640 L410 600 L455 615 C470 590 465 545 440 520 Z" fill="{SKIN}" stroke="{OUT}" stroke-width="7"/>
  <!-- braço direito -->
  <path d="M130 470 C60 500 40 580 70 640 C90 680 140 690 180 670 L220 640 L190 600 L145 615 C130 590 135 545 160 520 Z" fill="{SKIN}" stroke="{OUT}" stroke-width="7"/>
  <!-- tatuagens nos braços: palmeira, ondas, rosa-dos-ventos -->
  <g stroke="{INK}" stroke-width="4.5" fill="none">
    <path d="M85 610 q8 -40 30 -70"/><path d="M115 540 q-25 -5 -40 8"/><path d="M115 540 q-10 -22 -32 -26"/><path d="M115 540 q12 -20 34 -18"/><path d="M115 540 q20 -2 30 16"/>
    <path d="M80 640 q15 -8 30 0 t30 0"/><path d="M84 655 q15 -8 30 0 t30 0"/>
    <circle cx="500" cy="560" r="26"/><path d="M500 528 L500 592 M468 560 L532 560 M500 534 l6 26 -6 26 -6 -26 z"/>
    <path d="M455 630 q15 -8 30 0 t30 0"/>
  </g>
  <!-- controle branco genérico -->
  <g>
    <path d="M190 612 C200 588 240 580 300 584 C360 580 400 588 410 612 C428 650 440 700 418 712 C398 722 380 700 362 678 L238 678 C220 700 202 722 182 712 C160 700 172 650 190 612 Z"
          fill="#f7f7f9" stroke="{OUT}" stroke-width="6"/>
    <path d="M200 640 C215 625 250 622 300 624 C350 622 385 625 400 640" stroke="#d9dbe3" stroke-width="5" fill="none"/>
    <rect x="232" y="628" width="14" height="40" rx="3" fill="#3a3f4d"/><rect x="219" y="641" width="40" height="14" rx="3" fill="#3a3f4d"/>
    <circle cx="370" cy="634" r="7" fill="#22c1a1"/><circle cx="386" cy="648" r="7" fill="#ff5e62"/>
    <circle cx="354" cy="648" r="7" fill="#ffc145"/><circle cx="370" cy="662" r="7" fill="#4a7bff"/>
    <circle cx="272" cy="668" r="13" fill="#3a3f4d" stroke="{OUT}" stroke-width="3"/><circle cx="328" cy="668" r="13" fill="#3a3f4d" stroke="{OUT}" stroke-width="3"/>
    <rect x="282" y="600" width="36" height="16" rx="5" fill="#cfd3dd"/>
  </g>
  <!-- mãos segurando -->
  <path d="M168 640 C160 610 190 600 205 615 L215 650 C210 675 180 678 170 664 Z" fill="{SKIN}" stroke="{OUT}" stroke-width="6"/>
  <path d="M432 640 C440 610 410 600 395 615 L385 650 C390 675 420 678 430 664 Z" fill="{SKIN}" stroke="{OUT}" stroke-width="6"/>
  <!-- orelhas -->
  <ellipse cx="196" cy="268" rx="20" ry="30" fill="{SKIN}" stroke="{OUT}" stroke-width="6"/>
  <ellipse cx="404" cy="268" rx="20" ry="30" fill="{SKIN}" stroke="{OUT}" stroke-width="6"/>
  <!-- rosto -->
  <path d="M206 210 C206 150 250 120 300 120 C350 120 394 150 394 210 L394 290 C394 340 350 372 300 372 C250 372 206 340 206 290 Z" fill="{SKIN}" stroke="{OUT}" stroke-width="7"/>
  <!-- barba grisalha cheia -->
  <path d="M206 262 C214 300 226 318 246 330 C256 296 344 296 354 330 C374 318 386 300 394 262 C404 330 392 400 352 432 C330 450 270 450 248 432 C208 400 196 330 206 262 Z"
        fill="{BEARD}" stroke="{OUT}" stroke-width="6"/>
  <g stroke="{BEARD_SH}" stroke-width="4" fill="none">
    <path d="M240 370 q8 25 22 40"/><path d="M300 384 l0 44"/><path d="M360 370 q-8 25 -22 40"/><path d="M220 320 q4 30 18 52"/><path d="M380 320 q-4 30 -18 52"/>
  </g>
  <!-- bigode -->
  <path d="M244 304 C262 286 290 290 300 302 C310 290 338 286 356 304 C344 318 318 318 300 310 C282 318 256 318 244 304 Z" fill="{BEARD}" stroke="{OUT}" stroke-width="5"/>
  {mouth}
  <!-- nariz -->
  <path d="M296 262 q-16 26 2 34 q10 4 18 -2" stroke="{OUT}" stroke-width="5" fill="none"/>
  <!-- sobrancelhas grisalhas -->
  <path d="M238 228 q24 -16 46 -4" stroke="{BEARD_SH}" stroke-width="11" fill="none"/>
  <path d="M316 224 q22 -12 46 4" stroke="{BEARD_SH}" stroke-width="11" fill="none"/>
  {eyes}
  <!-- bochechas -->
  <ellipse cx="236" cy="286" rx="16" ry="9" fill="#ff8a7a" opacity=".45"/>
  <ellipse cx="364" cy="286" rx="16" ry="9" fill="#ff8a7a" opacity=".45"/>
  <!-- boné -->
  <path d="M196 196 C196 112 250 70 304 70 C362 70 410 112 410 192 C380 176 240 176 196 196 Z" fill="url(#cap)" stroke="{OUT}" stroke-width="7"/>
  <path d="M300 72 L300 184" stroke="{OUT}" stroke-width="4" opacity=".35"/>
  <path d="M250 82 Q240 130 244 182" stroke="{OUT}" stroke-width="3" opacity=".25" fill="none"/>
  <path d="M352 82 Q362 130 358 180" stroke="{OUT}" stroke-width="3" opacity=".25" fill="none"/>
  <circle cx="303" cy="72" r="9" fill="#ff3d7f" stroke="{OUT}" stroke-width="4"/>
  <path d="M190 196 C240 172 380 172 418 194 C450 206 470 222 462 232 C420 214 300 208 196 222 C180 214 180 204 190 196 Z" fill="url(#brim)" stroke="{OUT}" stroke-width="7"/>
  <!-- palmeira bordada no boné (marca própria, sem logo de terceiros) -->
  <g transform="translate(300 128) scale(.9)" stroke="#fff" stroke-width="5" fill="none">
    <path d="M0 34 q2 -22 8 -40"/><path d="M8 -6 q-16 -6 -26 4"/><path d="M8 -6 q-6 -16 -22 -18"/><path d="M8 -6 q8 -14 24 -12"/><path d="M8 -6 q16 0 22 12"/>
  </g>
</g>
</svg>'''
