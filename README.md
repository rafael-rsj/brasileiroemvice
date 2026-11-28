# guizo — o que acontece em Cascavel (PR)

Robô do perfil @guizocascavel: notícias e novidades da cidade, alertas (radar, trânsito, obra), agenda do fim de semana,
story do clima, reels e respostas a comentários. Roda sozinho no GitHub Actions (`.github/workflows/guizo.yml`).

- `config/settings.yaml`: fontes, palavras-chave, assuntos bloqueados e o botão `ativo` (true = publica).
- `config/pautas.yaml`: pautas suas que entram na frente da fila.
- Testar sem publicar: Actions → guizo → Run workflow → comando (post, agenda, clima, reel, fontes) e dry_run = 1.
