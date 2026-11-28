"""IA do guizo: escolhe a pauta de Cascavel, escreve título, legenda, roteiro do reel, agenda e respostas."""
import json
import os
import re

import anthropic

from news import load_cfg

PERSONA = """Você é o editor do "guizo" (@guizocascavel), perfil de Instagram sobre o que acontece em Cascavel (PR).
O feed é para o que faz a pessoa querer seguir: o que bombou e todo mundo está comentando, novidades da cidade
(lugar que abriu ou fechou, obra entregue, coisa nova), casos policiais que repercutiram muito e informação útil de
verdade (mudança no trânsito, obra grande, falta de água ou luz). Pense no "spotted" de cidade: é o assunto do dia
que a pessoa quer saber primeiro.
Tom: cascavelense, próximo e direto, com humor leve quando cabe; sério e respeitoso em caso policial, acidente ou tragédia.
Regras de ouro:
- NUNCA invente: data, horário, endereço, preço e números só se estiverem no texto das fontes.
- Caso policial: conte o fato sem sensacionalismo e sem detalhe gráfico. Nunca dê nome, foto ou pista de vítima,
  de menor de idade ou de suspeito que não foi condenado; diga "um homem de 30 anos", "a polícia", "o suspeito".
- Nada de suicídio, abuso sexual ou crime contra criança. Sem política partidária nem opinião sobre políticos.
- Nunca fale dos limites da fonte ("o título da matéria diz", "não temos mais detalhes no texto"): diga só o que se sabe
  e, se faltar algo importante, "mais detalhes em breve".
- Português do Brasil, frases curtas. Títulos sem caixa alta; use *asteriscos* em 1 a 3 palavras de destaque.
"""


def _client():
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


_MODEL = None


def _model(cfg) -> str:
    global _MODEL
    if _MODEL:
        return _MODEL
    wanted = cfg["ia"].get("modelo", "auto")
    ids = [m.id for m in _client().models.list(limit=100).data]
    _MODEL = wanted if wanted in ids else ([i for i in ids if "sonnet" in i] or ids)[0]
    print("Modelo de IA:", _MODEL)
    return _MODEL


def _text(msg) -> str:
    return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


def _ask(prompt: str, max_tokens: int = 4000) -> dict:
    cfg = load_cfg()
    msg = _client().messages.create(model=_model(cfg), max_tokens=max_tokens, system=PERSONA,
                                    messages=[{"role": "user", "content": prompt}])
    return _json(_text(msg))


def _idade(it: dict) -> str:
    from datetime import datetime, timezone
    if not it.get("published"):
        return "sem data"
    h = (datetime.now(timezone.utc) - datetime.fromisoformat(it["published"])).total_seconds() / 3600
    return f"há {max(int(h), 0)}h"


def pick_and_write(items: list[dict], recent_titles: list[str], momento: str = "", circulou: list[str] | None = None) -> dict | None:
    """Escolhe a melhor pauta entre as notícias novas e devolve tudo escrito (ou None se nada vale post)."""
    if not items:
        return None
    listing = "\n".join(f"[{i}] ({it['source']}, {_idade(it)}) {it['title']} — {it['summary'][:280]}" for i, it in enumerate(items[:45]))
    prompt = f"""Coisas novas sobre Cascavel coletadas agora ({momento or 'agora'}):
{listing}

FRESCOR É OBRIGATÓRIO: só vale fato que aconteceu nas últimas horas ou que ainda está em andamento/afeta a pessoa hoje.
Notícia de ontem que já circulou NÃO serve, mesmo que seja boa (o que foi, foi). Se o texto indica que o fato foi
"ontem", "na última sexta" ou antes, descarte. Item "sem data" só se o texto deixar claro que é de hoje.
Melhor pular do que postar coisa velha.

O QUE JÁ CIRCULOU (sites e páginas grandes da cidade postaram há horas; o público já viu):
{chr(10).join('- ' + c for c in (circulou or [])[:80]) or '- nada'}
Se a pauta for o MESMO ASSUNTO de algo dessa lista postado há mais de 6h, ela só vale se trouxer um FATO NOVO
(foi autorizado, data confirmada, alguém foi preso, saiu o resultado, abriu de fato, mudou algo). Nesse caso o título
começa pelo fato novo e o selo é "ATUALIZAÇÃO". Se for a mesma notícia contada de novo, descarte.
Assunto que as páginas grandes postaram há menos de 3h ainda está quente e pode ir, com um ângulo próprio.

Já postamos recentemente (não repita o assunto):
{chr(10).join('- ' + t for t in recent_titles[-20:]) or '- nada ainda'}

Escolha a pauta com MAIS potencial de a pessoa parar, comentar, mandar pra alguém e seguir a página. Prioridade:
1) BOMBOU: o assunto que a cidade inteira está comentando (fato curioso, polêmica local, flagrante, vídeo viral, algo absurdo);
2) POLICIA: caso policial que repercutiu muito ou é muito fora do comum (não o B.O. de todo dia);
3) NOVIDADE: lugar que abriu ou fechou, obra entregue, serviço novo, coisa diferente na cidade;
4) ALERTA: mudança que afeta muita gente agora (bloqueio grande, falta de água/luz, golpe circulando, mudança no trânsito);
5) CIDADE: problema ou conquista da cidade que interessa a muita gente;
6) EVENTO: só se for muito grande (show de artista conhecido, festival que para a cidade).
Quando couber, use no título um formato que está bombando: "POV: ...", "3 coisas que ...", "Antes e depois: ...",
"Você sabia que ...", "Cascavel acordou com ...". Sem forçar: só se combinar com o assunto.
Radar só entra se for algo grande (vários radares novos, radar que todo mundo reclama); radar isolado não vale post.
Evite notícia sem impacto, nota oficial burocrática e política. Agrupe itens do mesmo assunto.
Se nada servir, responda {{"skip": true}}.
Responda SOMENTE em JSON:
{{
 "skip": false,
 "indices": [números dos itens usados],
 "tipo": "BOMBOU|POLICIA|NOVIDADE|ALERTA|CIDADE|EVENTO",
 "selo": "selo curto da arte, ex: 'ABRIU', 'TODO MUNDO FALANDO', 'ATENÇÃO', 'DE GRAÇA' (máx. 22 caracteres)",
 "titulo": "título da arte com *destaque*, máx. 70 caracteres",
 "subtitulo": "1 frase de contexto, máx. 110 caracteres",
 "onde": "local/endereço se a fonte disser, senão vazio",
 "quando": "data/horário se a fonte disser, senão vazio",
 "dados": [{{"rotulo": "ex: LIMITE, PREÇO, HORÁRIO, A PARTIR DE", "valor": "ex: 50 km/h, grátis, 19h"}}] (0 a 2 itens, só com o que a fonte diz),
 "slide2_texto": "3 a 4 frases explicando o que se sabe, útil para o morador (máx. 400 caracteres)",
 "fonte_principal": "nome do veículo",
 "legenda": "legenda: 1ª linha gancho curto com 1 emoji; linha em branco; 2 a 3 frases com o essencial; se tiver, linhas com 📍 local e 🗓 data; termina com uma pergunta que puxe comentário (ex: 'Você já passou por lá?'). Sem hashtags. Use \\\\n",
 "legenda_facebook": "versão para a Página do Facebook, público de 30 a 60 anos de Cascavel: tom claro e informativo, sem gíria e sem 'POV'; 3 a 5 frases com o que aconteceu, onde, quando e por que importa (trânsito, serviço, segurança, família); se tiver, 📍 e 🗓; termina com uma pergunta simples para comentar. Sem hashtags. Use \\\\n",
 "hashtags": ["até 6 hashtags locais e do assunto"],
 "busca_foto": "2 a 4 palavras em inglês para foto ilustrativa SEM PESSOAS (objeto ou lugar), caso a matéria não tenha foto (ex: 'police car lights', 'speed camera road', 'water tap'); vazio se não fizer sentido",
 "story_pergunta": "pergunta curta para enquete no story (máx. 40 caracteres)",
 "reel_roteiro": "narração de 35 a 55 palavras, tom de amigo contando a novidade, termina com 'segue o guizo pra saber tudo de Cascavel'; números por extenso",
 "reel_narrar": true ou false
}}"""
    data = _ask(prompt)
    if data.get("skip"):
        return None
    data["used"] = [items[i] for i in data.get("indices", []) if 0 <= i < len(items)]
    if not data["used"]:
        return None
    return data


def engajamento(recent_titles: list[str], momento: str) -> dict | None:
    """Sem notícia fresca boa: post de conversa que faz o morador comentar, marcar alguém e salvar. Nada de fato inventado."""
    from datetime import datetime, timedelta, timezone
    agora = datetime.now(timezone(timedelta(hours=-3)))
    dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    data = _ask(f"""Hoje é {dias[agora.weekday()]}, {agora.day:02d}/{agora.month:02d}, {momento}. Não apareceu notícia nova que preste,
então o guizo vai postar algo para o pessoal de Cascavel comentar e se identificar.

Já postamos (não repita a ideia):
{chr(10).join('- ' + t for t in recent_titles[-25:]) or '- nada ainda'}

Escolha UM formato e crie o post:
- DEBATE: "Qual é o melhor ___ de Cascavel?" (xis, pastel, café da manhã, pizza, açaí, lugar pra levar visita, rolê de domingo...) — a resposta fica nos comentários;
- POV de morador: humor que todo cascavelense reconhece (frio de manhã e calor à tarde, vento, Avenida Brasil, Lago Municipal, garoa, sotaque, distância do litoral...);
- COMPLETE A FRASE: "Cascavel sem ___ não é Cascavel", "Só quem mora em Cascavel sabe que ___";
- ESSE OU ESSE: duas opções locais genéricas para votar nos comentários;
- MARCA ALGUÉM: "Marca aquele amigo que ___" com situação típica da cidade;
- de manhã cabe um "bom dia, Cascavel" leve com pergunta do dia; sexta/sábado cabe pergunta de rolê; domingo cabe clima de descanso.
REGRAS: não invente fato, número, data, preço, notícia, nem cite estabelecimento pelo nome (eles vêm nos comentários).
Nada de política, religião ou tema sensível. Tom leve, de amigo, sem ser infantil.
Responda SOMENTE em JSON:
{{
 "tipo": "CIDADE",
 "selo": "ex: 'COMENTA AÍ', 'DEBATE', 'SÓ QUEM MORA AQUI', 'MARCA ALGUÉM' (máx. 22 caracteres)",
 "titulo": "frase da arte com *destaque*, máx. 70 caracteres",
 "subtitulo": "1 frase curta que puxa a resposta, máx. 110 caracteres",
 "onde": "", "quando": "", "dados": [], "slide2_texto": "",
 "fonte_principal": "",
 "legenda": "1ª linha gancho com 1 emoji; linha em branco; 1 a 2 frases; termina com o pedido claro (comenta, marca, vota). Sem hashtags. Use \\n",
 "legenda_facebook": "versão para público de 30 a 60 anos, tom simpático e claro, sem gíria; termina com pergunta. Use \\n",
 "hashtags": ["até 5 hashtags locais"],
 "busca_foto": "",
 "story_pergunta": "pergunta curta para enquete (máx. 40 caracteres)",
 "reel_roteiro": "", "reel_narrar": false
}}""")
    if not data or not data.get("titulo"):
        return None
    data["used"] = []
    return data


def write_agenda(sources: list[dict], periodo: str, recent: list[str]) -> dict | None:
    """Monta a agenda (fim de semana) a partir do texto das páginas de eventos."""
    blocos = "\n\n".join(f"### {s['fonte']} ({s['url']})\n{s['texto']}" for s in sources)
    fotos, cat = [], []
    for s in sources:
        for im in s.get("imagens", []):
            cat.append(f"[F{len(fotos)}] ({s['fonte']}) {im['t']}")
            fotos.append({"src": im.get("src", ""), "link": im.get("link", ""), "fonte": s["fonte"]})
    prompt = f"""Textos copiados de sites de eventos e notícias de Cascavel (PR):
{blocos[:42000]}

Fotos dos cards de evento encontradas nessas páginas (código e texto do card):
{chr(10).join(cat[:120]) or '- nenhuma'}

Monte a agenda de "{periodo}" em Cascavel. Use SOMENTE eventos que estão nos textos acima, com data dentro desse
período (ou em cartaz o período todo). Não invente data, horário, local nem preço: se não souber, deixe vazio.
Prioridade: show bom (artista conhecido ou banda que lota), festa e balada com atração, festival, teatro, feira grande,
programa gratuito. Diga sempre o nome da casa de show ou do local, mesmo pequeno, e o dia da semana.
Ignore eventos de outras cidades. Se houver menos de 3 eventos confiáveis, responda {{"skip": true}}.
Responda SOMENTE em JSON:
{{
 "skip": false,
 "titulo_capa": "ex: 'O que fazer em *Cascavel*' (máx. 34 caracteres)",
 "eventos": [{{"nome": "nome do evento (máx. 46 caracteres)", "dia": "dia curto, ex: 'SEX 05'", "quando": "ex: 'sáb, 29/11 · 20h'", "onde": "local", "preco": "ex: 'grátis', 'a partir de R$ 40' ou vazio", "categoria": "SHOW|FESTA|TEATRO|FEIRA|GASTRONOMIA|ESPORTE|FAMÍLIA|CULTURA", "por_que_ir": "1 frase curta e animada (máx. 90 caracteres)", "destaques": ["0 a 2 detalhes curtos do que vai ter, só se estiver no texto (máx. 45 caracteres cada), ex: 'food trucks', 'brinquedos para as crianças'"], "foto": "código F do card DESTE evento (banner, notícia sobre ele, edição anterior) ou vazio se não tiver certeza que é dele", "fonte": "nome do site de onde veio"}}] (3 a 8 eventos, em ordem de data),
 "legenda": "legenda: 1ª linha gancho com 1 emoji; linha em branco; lista dos eventos, um por linha, com emoji da categoria, nome, dia e local; termina com 'Marca quem vai com você 👇' e 'Tem evento? Manda no direct que a gente divulga'. Sem hashtags. Use \\\\n",
 "hashtags": ["até 6 hashtags"]
}}"""
    data = _ask(prompt, 6000)
    if data.get("skip") or len(data.get("eventos", [])) < 3:
        return None
    from news import og_image
    for e in data["eventos"]:
        e["img"], e["credito"] = None, ""
        m = re.fullmatch(r"F(\d+)", str(e.get("foto", "")).strip())
        if m and int(m.group(1)) < len(fotos):
            f = fotos[int(m.group(1))]
            src = f["src"] or (og_image(f["link"]) if f.get("link") else None)
            if not src and f.get("link") and f["src"] == "":
                src = None
            if src:
                e["img"], e["credito"] = src, f"Foto: divulgação/{f['fonte']}"
    return data


def reply_comment(post_caption: str, comment: str) -> str | None:
    cfg = load_cfg()
    msg = _client().messages.create(
        model=_model(cfg), max_tokens=1500,
        system=PERSONA + """
Você está respondendo comentários no SEU post. Seja simpático e cascavelense, curto (máx. 140 caracteres), 1 emoji no máximo.
Se a pessoa sugerir pauta ou evento, agradeça e peça para mandar no direct.
Não responda (devolva exatamente SKIP) se for spam, ofensa, briga política, propaganda, link, só emoji,
ou se exigir uma informação que você não tem certeza.""",
        messages=[{"role": "user", "content": f"Legenda do post:\n{post_caption}\n\nComentário:\n{comment}"}])
    out = _text(msg).strip()
    return None if out.upper().startswith("SKIP") else out


def avaliar_pauta(material: str) -> dict:
    """Pauta mandada pelo dono (link, reel, texto): decide se vale post e resume com palavras próprias."""
    return _ask(f"""O dono da página mandou esta possível pauta (pode ser link de matéria, post ou reel de outro perfil, ou texto):
{material[:6000]}

Decida se vale post no guizo (Cascavel-PR). Vale se for de Cascavel ou região, recente e interessante
(bombou, novidade, evento bom, caso que repercutiu, informação útil). Não vale se for velho, de outra cidade,
boato sem fonte, propaganda pura ou já muito batido.
Reescreva com palavras próprias, sem copiar frases do original.
Responda SOMENTE em JSON: {{"vale": true/false, "motivo": "curto, se não vale", "titulo": "título curto do assunto",
"resumo": "3 a 5 frases com os fatos (quem, o quê, onde, quando), sem inventar nada", "fonte": "veículo ou perfil de origem, se souber"}}""", 1500)


def comentario_para(perfil: str, legenda: str, img_url: str | None) -> str | None:
    """Comentário do guizo em post de outro perfil (o dono cola na mão). None = melhor não comentar."""
    cfg = load_cfg()
    prompt = f"""Post recente do perfil @{perfil} (Cascavel-PR). Legenda:
{(legenda or '(sem legenda)')[:1500]}

Escreva o comentário que o perfil guizo (página sobre Cascavel) vai deixar nesse post.
Regras:
- Curto (máx. 90 caracteres), natural, como gente da cidade falando. Nada de "segue a gente", link ou propaganda.
- Rolê, comida, lugar, show, novidade: descontraído e divertido, que faça sentido com o post.
- Coisa fofa (bicho, criança, homenagem): carinhoso.
- Natal: pode usar emoji de natal 🎄✨🎅.
- Notícia tensa (acidente, crime, morte, tragédia, doença): responda SÓ com 1 ou 2 destes emojis: 😢 😮 😨 🥀 🙏 — nenhuma palavra.
- Política, briga, sorteio, post patrocinado ou assunto que você não entendeu: responda exatamente SKIP.
Responda só com o comentário (ou SKIP)."""
    content = [{"type": "text", "text": prompt}]
    if img_url:
        content.insert(0, {"type": "image", "source": {"type": "url", "url": img_url}})
    try:
        msg = _client().messages.create(model=_model(cfg), max_tokens=300, system=PERSONA,
                                        messages=[{"role": "user", "content": content}])
    except Exception:
        msg = _client().messages.create(model=_model(cfg), max_tokens=300, system=PERSONA,
                                        messages=[{"role": "user", "content": prompt}])
    out = _text(msg).strip().strip('"')
    return None if not out or out.upper().startswith("SKIP") else out


def plantao(items: list[dict], hoje: list[str]) -> dict:
    """Plantão: entre as notícias das últimas horas, existe algo URGENTE que não pode esperar o próximo horário?"""
    listing = "\n".join(f"[{i}] ({it['source']}) {it['title']} — {it['summary'][:240]}" for i, it in enumerate(items[:30]))
    return _ask(f"""Notícias de Cascavel das últimas horas:
{listing}

O que o guizo já postou hoje (horário e título):
{chr(10).join('- ' + t for t in hoje) or '- nada ainda'}

Você é o plantão do guizo. Só marque urgente o que um morador de Cascavel precisa saber AGORA e que a cidade inteira
vai comentar: acidente grave ou que travou uma via importante, incêndio grande, temporal/enchente, queda de energia
ou falta de água em muitos bairros, interdição grande, crime de enorme repercussão, fato muito fora do comum.
Notícia comum, nota oficial, evento ou novidade NÃO é urgente (essas esperam o horário normal).
Se já postamos sobre o assunto hoje, só marque "atualizacao" se houver informação nova e importante (ex.: liberação da via,
estado das vítimas, causa confirmada).
Responda SOMENTE em JSON: {{"urgente": false}} ou
{{"urgente": true, "modo": "novo" ou "atualizacao", "indices": [itens usados], "motivo": "1 frase"}}""", 800)
