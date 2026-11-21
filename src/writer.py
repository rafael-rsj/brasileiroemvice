"""Usa IA para escolher a melhor pauta, checar se é fato ou rumor e escrever manchete + legenda."""
import json
import os
import re

import anthropic

from news import load_cfg

PERSONA = """Você é o editor do perfil de Instagram "Brasileiro em Vice" (@brasileiroemvice),
página brasileira de notícias e curiosidades de GTA 6. Tom: animado, brasileiro, direto, com humor leve,
sem exagero e SEM inventar fatos. Nunca afirme algo que as fontes não dizem.
Regras:
- Se só fontes não confiáveis (Reddit, agregadores) falam do assunto, ou se há menos de {min_src} fontes
  confiáveis, a tag é RUMOR e o texto deixa claro que não é confirmado.
- Se a fonte é a própria Rockstar/Take-Two, tag OFICIAL.
- Nunca divulgue pirataria, cracks, downloads, links suspeitos ou spoilers pesados de história sem aviso.
- Manchete curta (máx. 75 caracteres), em português, MAIÚSCULAS não são necessárias. Coloque entre *asteriscos*
  1 a 3 palavras de destaque.
"""


def _client():
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


_MODEL = None


def _model(cfg) -> str:
    """Usa o modelo do settings.yaml; se for 'auto' ou não existir mais, pega o Sonnet mais novo disponível."""
    global _MODEL
    if _MODEL:
        return _MODEL
    wanted = cfg["ia"].get("modelo", "auto")
    ids = [m.id for m in _client().models.list(limit=100).data]
    if wanted in ids:
        _MODEL = wanted
    else:
        sonnets = [i for i in ids if "sonnet" in i]
        _MODEL = (sonnets or ids)[0]  # a lista vem do mais novo para o mais antigo
    print("Modelo de IA:", _MODEL)
    return _MODEL


def _text(msg) -> str:
    """Junta só os blocos de texto da resposta (ignora blocos de raciocínio)."""
    return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


def pick_and_write(items: list[dict], recent_titles: list[str]) -> dict | None:
    """Recebe as notícias novas e devolve a pauta escolhida já escrita, ou None se nada vale post."""
    if not items:
        return None
    cfg = load_cfg()
    listing = "\n".join(
        f"[{i}] ({it['source']}{', confiável' if it['trusted'] else ''}) {it['title']} — {it['summary'][:300]}"
        for i, it in enumerate(items[:40]))
    prompt = f"""Notícias novas coletadas agora:
{listing}

Já postamos recentemente (não repita o assunto):
{chr(10).join('- ' + t for t in recent_titles[-15:]) or '- nada ainda'}

Escolha a pauta MAIS relevante e com mais potencial de engajamento para fãs brasileiros de GTA 6.
Agrupe itens que falam do mesmo assunto para contar as fontes. Se nada for relevante, responda {{"skip": true}}.
Responda SOMENTE em JSON:
{{
 "skip": false,
 "indices": [números dos itens usados],
 "tag": "OFICIAL|NOTICIA|RUMOR|CURIOSIDADE",
 "titulo": "manchete com *destaque*",
 "subtitulo": "1 frase de contexto, máx. 110 caracteres",
 "estrelas": 1-5 (o quão bombástica é a notícia),
 "fonte_principal": "nome do veículo",
 "legenda": "legenda do post em PT-BR, 3 a 6 linhas curtas, com 2-4 emojis, terminando com uma PERGUNTA para gerar comentários",
 "hashtags": ["até 8 hashtags relevantes, sem as fixas"],
 "story_pergunta": "pergunta curta para enquete no story (máx. 40 caracteres)",
 "slide2_rotulo": "rótulo curto do dado principal, ex: 'Tempo para zerar:' ou 'O que muda:' (máx. 24 caracteres)",
 "slide2_valor": "o dado em destaque, ex: '82 horas' (máx. 18 caracteres, pode ficar vazio)",
 "slide2_texto": "2 a 4 frases explicando a notícia com contexto para o fã brasileiro, sem inventar nada (máx. 380 caracteres)",
 "reel_roteiro": "texto para narração do reel, 35 a 60 palavras, tom de plantão animado, termina pedindo para seguir a página; números por extenso",
 "reel_narrar": true ou false (true quando a notícia rende explicação falada; false quando é algo visual/rápido que fica melhor só com música)
}}"""
    msg = _client().messages.create(
        model=_model(cfg), max_tokens=max(4000, cfg["ia"]["max_tokens"]),
        system=PERSONA.format(min_src=cfg["seguranca"]["fontes_minimas_para_fato"]),
        messages=[{"role": "user", "content": prompt}])
    data = _json(_text(msg))
    if data.get("skip"):
        return None
    used = [items[i] for i in data.get("indices", []) if 0 <= i < len(items)]
    trusted = sum(1 for u in used if u["trusted"])
    # trava de segurança independente da IA
    min_src = cfg["seguranca"]["fontes_minimas_para_fato"]
    downgraded = (data["tag"] == "NOTICIA" and trusted < min_src) or (data["tag"] == "OFICIAL" and trusted < 1)
    if downgraded:
        # reescreve para o texto não afirmar como fato o que a trava marcou como rumor
        fix = _client().messages.create(
            model=_model(cfg), max_tokens=4000,
            system=PERSONA.format(min_src=min_src),
            messages=[{"role": "user", "content": prompt},
                      {"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                      {"role": "user", "content": "As fontes confiáveis não bastam para tratar isso como fato. "
                       "Reescreva TUDO como RUMOR (tag RUMOR), sem dizer 'oficial' ou 'confirmado', deixando claro "
                       "que ainda não há confirmação. Mesmo formato JSON."}])
        data = _json(_text(fix))
        data["tag"] = "RUMOR"
    data["used"] = used
    return data


def reply_comment(post_caption: str, comment: str) -> str | None:
    """Gera uma resposta curta para um comentário no nosso post. None = não responder."""
    cfg = load_cfg()
    msg = _client().messages.create(
        model=_model(cfg), max_tokens=2000,
        system=PERSONA.format(min_src=2) + """
Você está respondendo comentários no SEU post. Seja simpático, curto (máx. 140 caracteres), 1 emoji no máximo.
Não responda (devolva exatamente SKIP) se o comentário for spam, ofensivo, propaganda, link, só emoji,
ou se exigir uma informação que você não tem certeza.""",
        messages=[{"role": "user", "content": f"Legenda do post:\n{post_caption}\n\nComentário:\n{comment}"}])
    out = _text(msg).strip()
    return None if out.upper().startswith("SKIP") else out
