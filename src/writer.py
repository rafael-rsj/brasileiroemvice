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
 "legenda": "legenda estilo portal que dá vontade de ler: 1ª linha = gancho forte em MAIÚSCULAS com 1 emoji (ex: '🚨 ROCKSTAR CONFIRMOU O QUE TODO MUNDO PEDIA'); depois linha em branco e 2 a 3 parágrafos curtos explicando o que se sabe; depois 3 a 4 tópicos curtos com emoji no começo (📍 ✅ ⚠️ 🎮 💰 etc.) com os pontos principais; termina com uma PERGUNTA que provoca opinião. Sem hashtags e sem pedir para seguir (isso é adicionado depois). Use quebras de linha \\n",
 "comentario_tio": "comentário engraçado e curto do Tio Vice (mascote coroa gamer) reagindo à notícia, máx. 80 caracteres, sem inventar fatos",
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


TEMAS_DICAS = [
    "relacionamento e games (o que gamers queriam ouvir do parceiro ou parceira, e vice-versa)",
    "o que mulheres gamers queriam que os caras entendessem",
    "dicas de GTA 6 para iniciantes", "segredos e truques de GTA 6", "como economizar comprando jogos",
    "setup gamer barato e ergonomia", "saúde do gamer (postura, vista, sono)", "etiqueta no online e no chat de voz",
    "jogos para jogar em casal", "sinais de que você virou viciado em GTA (humor)", "dicas para PS5 e Xbox que pouca gente conhece",
    "regras não escritas de quem joga com amigos", "como convencer a família a liberar o videogame (humor)",
    "coisas que só quem jogou GTA San Andreas entende", "dinheiro e trabalho: profissões no mundo dos games",
]


def write_tips(recent_titles: list[str], seed: int) -> dict:
    """Carrossel de dicas do Tio Vice (mascote coroa, gamer, bem-humorado)."""
    cfg = load_cfg()
    tema = TEMAS_DICAS[seed % len(TEMAS_DICAS)]
    prompt = f"""Crie um carrossel viral de dicas para o Instagram, apresentado pelo Tio Vice, mascote da página:
um coroa brasileiro gamer, bem-humorado, sábio e sem papas na língua, mas respeitoso.
Tema de hoje: {tema}.
Já postamos (não repita): {"; ".join(recent_titles[-20:]) or "nada ainda"}.
Regras: humor leve e afetuoso, sem estereótipos ofensivos, sem machismo, sem humilhar ninguém; nada de conteúdo sexual.
Dicas práticas e que geram identificação ("é exatamente isso!"). Português do Brasil, informal.
Responda SOMENTE em JSON:
{{
 "titulo": "título curto e chamativo tipo lista, ex: '7 regras para jogar online' (máx. 48 caracteres), com 1 palavra entre *asteriscos*",
 "publico": "homens|mulheres|todos|casais",
 "dicas": [{{"titulo": "dica em até 40 caracteres", "texto": "explicação em até 150 caracteres"}}] (de 5 a 8 itens),
 "legenda": "legenda que prende: 1ª linha gancho em MAIÚSCULAS com 1 emoji; linha em branco; 2 frases engraçadas de identificação; depois a lista das dicas resumidas, uma por linha, começando com 1️⃣ 2️⃣ 3️⃣...; termina pedindo para comentar o número da dica favorita e marcar alguém que precisa ler. Sem hashtags. Use quebras de linha \\n",
 "hashtags": ["até 8 hashtags"]
}}"""
    msg = _client().messages.create(model=_model(cfg), max_tokens=4000, system=PERSONA.format(min_src=2),
                                    messages=[{"role": "user", "content": prompt}])
    return _json(_text(msg))


GUIA_TIPOS = ("guia, lista, ranking, segredos, easter eggs, localização de itens/carros/animais, códigos e truques, "
              "dicas de configuração, melhores carros/armas, atividades, personagens, comparações, curiosidades do mapa")


def write_guide(items: list[dict], recent_titles: list[str]) -> dict | None:
    """Carrossel estilo portal (guia/lista/segredos) a partir de uma matéria com texto completo.
    Passo 1: escolhe a matéria que rende lista. Passo 2: lê a matéria e escreve os slides só com o que ela diz."""
    from news import article_text
    cands = [it for it in items if it.get("link") and "news.google." not in it["link"]][:40]
    if not cands:
        return None
    cfg = load_cfg()
    listing = "\n".join(f"[{i}] ({it['source']}) {it['title']} — {it['summary'][:200]}" for i, it in enumerate(cands))
    msg = _client().messages.create(
        model=_model(cfg), max_tokens=2000, system=PERSONA.format(min_src=2),
        messages=[{"role": "user", "content": f"""Matérias recentes:
{listing}

Já postamos (não repita o assunto): {"; ".join(recent_titles[-25:]) or "nada"}

Quais matérias rendem um CARROSSEL DE LISTA para fãs de GTA 6 ({GUIA_TIPOS})? Precisa ter pelo menos 4 itens
concretos dentro do texto. Responda SOMENTE em JSON: {{"indices": [até 3 números, do melhor para o pior]}} ou {{"indices": []}}"""}])
    idx = [i for i in _json(_text(msg)).get("indices", []) if 0 <= i < len(cands)]
    for i in idx:
        it = cands[i]
        texto = article_text(it["link"])
        if len(texto) < 800:
            continue
        prompt = f"""Matéria de {it['source']} ({it['link']}):
TÍTULO: {it['title']}
TEXTO:
{texto[:9000]}

Transforme esta matéria em um carrossel de Instagram estilo portal de games (lista/guia), em PT-BR, com nossas
próprias palavras (não copie frases). Use SOMENTE informações que estão no texto. Se o texto não tiver pelo menos
4 itens concretos, responda {{"skip": true}}.
Responda SOMENTE em JSON:
{{
 "skip": false,
 "titulo": "título da capa tipo lista/guia, chamativo, máx. 52 caracteres, com 1 a 2 palavras entre *asteriscos* (ex: '7 *segredos* de Vice City que pouca gente viu')",
 "chamada": "selo curto da capa, ex: 'GUIA GTA 6', 'SEGREDOS', 'TOP 5', 'CÓDIGOS' (máx. 16 caracteres)",
 "slides": [{{"titulo": "item em até 34 caracteres com 1 palavra entre *asteriscos*", "texto": "explicação útil em até 190 caracteres", "selo": "CONFIRMADO|RUMOR|DICA|SEGREDO|ATENCAO", "cena": "2 a 4 palavras do assunto do item para escolher a imagem, ex: 'jason carro praia'"}}] (4 a 8 itens),
 "legenda": "legenda que prende: 1ª linha gancho em MAIÚSCULAS com 1 emoji; linha em branco; 1 parágrafo curto; depois os itens resumidos, um por linha, começando com 1️⃣ 2️⃣ 3️⃣...; termina com uma pergunta. Sem hashtags. Use \\n",
 "hashtags": ["até 8 hashtags"],
 "tema": "palavras do assunto geral para escolher a imagem da capa"
}}
Selo: CONFIRMADO só se a matéria diz que é oficial/confirmado pela Rockstar ou comprovado no jogo; RUMOR se a matéria trata como
boato/vazamento/especulação; senão DICA ou SEGREDO."""
        out = _json(_text(_client().messages.create(model=_model(cfg), max_tokens=4000, system=PERSONA.format(min_src=2),
                                                     messages=[{"role": "user", "content": prompt}])))
        if out.get("skip") or len(out.get("slides", [])) < 4:
            continue
        out["fonte"] = it["source"]
        out["used"] = [it]
        return out
    return None
