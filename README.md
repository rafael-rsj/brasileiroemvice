# 🇧🇷 Brasileiro em Vice — robô do Instagram

Robô do perfil [@brasileiroemvice](https://instagram.com/brasileiroemvice): notícias de GTA 6 com HUD próprio,
stories e respostas a comentários, tudo publicado pela API oficial do Instagram e agendado no GitHub Actions.

## O que roda sozinho

| Workflow | Quando (Brasília) | O que faz |
|---|---|---|
| `post.yml` | 12h, 18h, 21h | Busca notícias, IA escolhe a pauta, checa fato x rumor, gera a arte 4:5 e publica com legenda |
| `story.yml` | 9h, 13h, 16h, 19h40, 22h40 | Publica a versão 9:16 do último post ("Veja no feed") |
| `comments.yml` | de hora em hora | Responde comentários novos nos 6 posts mais recentes (máx. 15 por hora, ignora spam) |
| `refresh-token.yml` | dias 1 e 15 | Renova o token do Instagram antes de vencer (60 dias) |

Todos podem ser disparados na mão em **Actions → (workflow) → Run workflow**. Com `dry_run = 1` ele gera tudo e não publica.

## Travas de segurança (modo 100% automático)
- Notícia só sai como fato com **2+ fontes confiáveis**; menos que isso vira **RUMOR** com aviso na legenda.
- Tag **OFICIAL** só com pelo menos 1 fonte confiável.
- Ignora notícias com mais de 36h, repetidas ou com termos de pirataria (`config/settings.yaml`).
- Imagens geradas por IA recebem o selo oficial do Instagram (`is_ai_generated`).

## Secrets necessários (Settings → Secrets and variables → Actions)
| Nome | De onde vem |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `IG_ACCESS_TOKEN` | Token longo do app Meta (passo 2 abaixo) |
| `IG_USER_ID` | ID da conta Instagram (aparece junto do token) |
| `GH_PAT` | (opcional) token do GitHub com permissão de *Secrets* deste repo, para a renovação automática |

## Passo a passo da integração
1. **Instagram** ✅ conta comercial, categoria "Criador de conteúdo de vídeo de jogos".
2. **App na Meta** — developers.facebook.com → Criar app → caso de uso *"Gerenciar mensagens e conteúdo no Instagram"*
   → API do Instagram com login do Instagram → adicionar a conta @brasileiroemvice como testadora →
   gerar token com `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_comments`.
   Para uso só na própria conta, o app pode ficar em modo de desenvolvimento.
3. **Chave da IA** — criar a chave em console.anthropic.com e colocar créditos (≈ US$ 5–10/mês neste volume).
4. **Secrets** — cadastrar os 3 secrets acima.
5. **Teste** — Actions → *Post no feed* → Run workflow com `dry_run = 1`, conferir a arte em `media/`, depois rodar com `0`.

## Próximas etapas
- Reels automáticos (trechos curtos de trailer + narração IA + legenda + HUD) com ffmpeg.
- Carrosséis de comparação GTA 6 x 5 x 4.
- Imagens geradas por IA (cenários de Leonida, sem personagens oficiais).
- Mídias em Cloudflare R2 se o repositório precisar ficar privado.

## Estrutura
```
config/settings.yaml   fontes, palavras-chave, travas, horários
templates/card.html    HUD (feed 1080x1350 e story 1080x1920)
src/news.py            coleta e deduplicação
src/writer.py          IA editora (pauta, manchete, legenda, respostas)
src/render.py          gera as artes com Playwright
src/instagram.py       API oficial do Instagram
src/main.py            comandos: post | story | comments | refresh | demo
state/                 memória do robô (o que já postou/respondeu)
media/                 artes publicadas (servidas por URL pública para o Instagram)
```

> Página de fã, sem vínculo com a Rockstar Games ou Take-Two Interactive.
