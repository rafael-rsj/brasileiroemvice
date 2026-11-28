"""Post e story de lançamento do guizo (roda uma vez: python src/main.py lancamento)."""
from art import HANDLE, K, Y, asset, page, seal

LEGENDA = """Chegou o guizo 🐍

Tudo que acontece em Cascavel num lugar só: o que bombou, o que abriu, o que deu o que falar e onde ir.

Viu alguma coisa na cidade? Manda no direct ou marca o @guizocascavel no story que a gente espalha 📣

Segue e ativa o sininho 🔔

#Cascavel #CascavelPR #guizo #OesteDoParana"""


LEGENDA_FB = """Chegou o Guizo, a página de quem mora em Cascavel 🐍

Aqui você fica sabendo primeiro do que acontece na cidade: notícias que repercutiram, alertas de trânsito e de serviços, o que abriu de novo e os eventos do fim de semana.

Viu alguma coisa acontecendo? Mande uma mensagem para a página que a gente divulga.

Curta e siga a página para acompanhar 👍

#Cascavel #CascavelPR #OesteDoParana"""


def launch(h):
    bg = asset("fundo_cidade.jpg").as_uri()
    post=h==1350
    IH=700 if post else 1010
    return page(f'''<div class="abs" style="inset:0;background:#111"></div>
<img class="abs" src="{bg}" style="left:0;top:{-170 if post else 0}px;width:1080px;height:1350px">
<div class="abs" style="left:0;right:0;top:{IH-260}px;height:260px;background:linear-gradient(180deg,rgba(17,17,17,0),#111)"></div>
<div class="abs" style="left:56px;top:{52 if post else 130}px">{seal(size=52)}</div>
<div class="abs" style="right:56px;top:{70 if post else 150}px"><span class="tag" style="background:{K};color:{Y};font-size:28px">LANÇAMENTO</span></div>
<div class="abs" style="left:56px;right:56px;top:{IH-40}px">
 <div style="font-weight:800;font-size:38px;color:{Y};letter-spacing:3px">CHEGOU O GUIZO</div>
 <h1 style="font-size:{112 if post else 118}px;line-height:1;margin-top:14px">Cascavel na<br><span style="background:{Y};color:{K};padding:0 14px">palma</span> da mão.</h1>
 <div style="font-weight:600;font-size:{36 if post else 42}px;color:rgba(255,255,255,.88);margin-top:24px;line-height:1.35">O que tá acontecendo, o que abriu,<br>o que deu o que falar e onde ir.</div>
 <div style="margin-top:28px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
  {''.join(f'<div style="background:rgba(255,255,255,.08);border:2px solid rgba(255,255,255,.18);border-radius:12px;padding:14px 0;text-align:center;font-weight:800;letter-spacing:1.5px;color:#fff;font-size:{23 if post else 27}px">{t}</div>' for t in ["ROLÊS","SHOWS","NOVIDADES","OBRAS","POLÍCIA","TRÂNSITO","BOMBOU","MANDA AÍ"])}
 </div>
</div>
{'<div class="handle">'+HANDLE+'</div><div class="abs" style="right:56px;bottom:56px;font-weight:800;font-size:28px;color:'+Y+'">SEGUE E ATIVA O 🔔</div>' if post else '<div class="abs" style="left:0;right:0;bottom:150px;display:flex;justify-content:center"><span class="tag" style="background:'+Y+';color:'+K+';font-size:38px;padding:18px 34px">SEGUE O '+HANDLE+' <b style="font-size:50px;line-height:0;vertical-align:-4px">↑</b></span></div>'}''', h=h)
