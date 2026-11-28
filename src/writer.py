"""IA do guizo: escolhe a pauta de Cascavel, escreve título, legenda, roteiro do reel, agenda e respostas."""
import json
import os
import re

import anthropic

from news import load_cfg

PERSONA = """Você é o editor do "guizo" (@guizocascavel), perfil de Instagram sobre o que acontece em Cascavel (PR):
eventos e o que fazer, novidades da cidade (lugares que abriram, obras entregues, coisas novas), alertas úteis
(radar novo ou removido, interdição, obra, falta de água/luz, mudança no trânsito) e problemas da cidade.
O nome vem do guizo da cascavel: o barulho que avisa. Tom: cascavelense, próximo, leve e direto, com uma pitada de
humor quando cabe; sério e respeitoso quando o assunto é problema ou acidente.
Regras de ouro:
- NUNCA invente: data, horário, endereço, preço e números só se estiverem no texto das fontes.
- Não expor pessoas: sem nomes de vítimas, suspeitos ou menores; nada de violência explícita, morte ou crime pesado.
- Não fazer política partidária nem opinar sobre políticos.
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


def pick_and_write(items: list[dict], recent_titles: list[str]) -> dict | None:
    """Escolhe a melhor pauta entre as notícias novas e devolve tudo escrito (ou None se nada vale post)."""
    if not items:
        return None
    listing = "\n".join(f"[{i}] ({it['source']}) {it['title']} — {it['summary'][:280]}" for i, it in enumerate(items[:45]))
    prompt = f"""Coisas novas sobre Cascavel coletadas agora:
{listing}

Já postamos recentemente (não repita o assunto):
{chr(10).join('- ' + t for t in recent_titles[-20:]) or '- nada ainda'}

Escolha a pauta com MAIS potencial de engajamento para quem mora em Cascavel. Prioridade:
1) NOVIDADE: lugar que abriu/vai abrir, obra entregue, serviço novo, coisa diferente na cidade;
2) ALERTA: radar novo ou removido, interdição, obra que muda o trânsito, falta de água/luz, golpe circulando;
3) EVENTO: show, feira, festival, evento gratuito, algo grande que vai movimentar a cidade;
4) CIDADE: problema que afeta muita gente (buraco, fila, atraso de obra), curiosidade, conquista da cidade.
Evite notícia policial comum e política. Agrupe itens do mesmo assunto. Se nada servir, responda {{"skip": true}}.
Responda SOMENTE em JSON:
{{
 "skip": false,
 "indices": [números dos itens usados],
 "tipo": "NOVIDADE|ALERTA|EVENTO|CIDADE",
 "selo": "selo curto da arte, ex: 'NOVIDADE NA CIDADE', 'RADAR NOVO', 'ALERTA NO TRÂNSITO', 'VAI TER', 'DE GRAÇA', 'ATENÇÃO' (máx. 22 caracteres)",
 "titulo": "título da arte com *destaque*, máx. 70 caracteres",
 "subtitulo": "1 frase de contexto, máx. 110 caracteres",
 "onde": "local/endereço se a fonte disser, senão vazio",
 "quando": "data/horário se a fonte disser, senão vazio",
 "dados": [{{"rotulo": "ex: LIMITE, PREÇO, HORÁRIO, A PARTIR DE", "valor": "ex: 50 km/h, grátis, 19h"}}] (0 a 2 itens, só com o que a fonte diz),
 "slide2_texto": "3 a 4 frases explicando o que se sabe, útil para o morador (máx. 400 caracteres)",
 "fonte_principal": "nome do veículo",
 "legenda": "legenda: 1ª linha gancho curto com 1 emoji; linha em branco; 2 a 3 frases com o essencial; se tiver, linhas com 📍 local e 🗓 data; termina com uma pergunta que puxe comentário (ex: 'Você já passou por lá?'). Sem hashtags. Use \\\\n",
 "hashtags": ["até 6 hashtags locais e do assunto"],
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


def write_agenda(sources: list[dict], periodo: str, recent: list[str]) -> dict | None:
    """Monta a agenda (fim de semana) a partir do texto das páginas de eventos."""
    blocos = "\n\n".join(f"### {s['fonte']} ({s['url']})\n{s['texto']}" for s in sources)
    prompt = f"""Textos copiados de sites de eventos e notícias de Cascavel (PR):
{blocos[:42000]}

Monte a agenda de "{periodo}" em Cascavel. Use SOMENTE eventos que estão nos textos acima, com data dentro desse
período (ou em cartaz o período todo). Não invente data, horário, local nem preço: se não souber, deixe vazio.
Prefira variedade: show, festa, teatro, feira, gastronomia, esporte, programa gratuito, coisa para família.
Ignore eventos de outras cidades. Se houver menos de 3 eventos confiáveis, responda {{"skip": true}}.
Responda SOMENTE em JSON:
{{
 "skip": false,
 "titulo_capa": "ex: 'O que fazer em *Cascavel*' (máx. 34 caracteres)",
 "eventos": [{{"nome": "nome do evento (máx. 46 caracteres)", "quando": "ex: 'sáb, 29/11 · 20h'", "onde": "local", "preco": "ex: 'grátis', 'a partir de R$ 40' ou vazio", "categoria": "SHOW|FESTA|TEATRO|FEIRA|GASTRONOMIA|ESPORTE|FAMÍLIA|CULTURA", "por_que_ir": "1 frase curta e animada (máx. 90 caracteres)", "fonte": "nome do site de onde veio"}}] (3 a 8 eventos, em ordem de data),
 "legenda": "legenda: 1ª linha gancho com 1 emoji; linha em branco; lista dos eventos, um por linha, com emoji da categoria, nome, dia e local; termina com 'Marca quem vai com você 👇' e 'Tem evento? Manda no direct que a gente divulga'. Sem hashtags. Use \\\\n",
 "hashtags": ["até 6 hashtags"]
}}"""
    data = _ask(prompt, 5000)
    if data.get("skip") or len(data.get("eventos", [])) < 3:
        return None
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
