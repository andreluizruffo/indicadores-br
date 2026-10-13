# Plano da fase 2: no ar, com coleta diária

**Objetivo:** um link público com o painel e a API, e dados atualizados todo dia sem ninguém rodar nada.

**Fora do escopo desta fase:** novos indicadores, login, domínio próprio.

Cada etapa é entregue e conferida sozinha. Só passa para a próxima quando o critério de pronto da anterior estiver ok.

## Etapa 1: banco PostgreSQL hospedado

- Criar um banco no plano gratuito de um serviço de Postgres gerenciado (Neon ou Supabase, numa conta pessoal).
- Guardar a URL de conexão como secret `DATABASE_URL` no repositório do GitHub. Nunca no código.
- Rodar a carga completa uma vez a partir do PC: `DATABASE_URL=... uv run indicadores`.

**Pronto quando:** as 5 séries têm dados desde 2015 no banco hospedado e `execucoes` mostra status `ok` para todas.

## Etapa 2: coleta diária no GitHub Actions

- Novo workflow `coleta.yml` com `schedule` (todo dia útil à noite, depois da publicação da PTAX) e `workflow_dispatch` (botão para rodar na mão).
- Ele roda `uv run indicadores` com o secret `DATABASE_URL`.
- Se a coleta falhar, o job fica vermelho e o GitHub manda e-mail.

**Pronto quando:** duas execuções agendadas seguidas aparecem verdes, e a segunda grava só o dia novo.

**Cuidado:** em repositório público, o GitHub desliga workflows agendados depois de 60 dias sem atividade no repositório. Conferir de vez em quando ou fazer um commit.

## Etapa 3: API e painel no ar

- Publicar a imagem Docker que já existe num serviço com plano gratuito para web (ex.: Render), apontando para o mesmo `DATABASE_URL`.
- No plano gratuito o serviço "dorme" sem acesso e demora para acordar na primeira visita. Para portfólio é aceitável, mas vale avisar no painel ("carregando, pode levar alguns segundos").

**Pronto quando:** o link público abre o painel com os valores de hoje, e `/docs` funciona.

## Etapa 4: divulgar

- Link no topo do README, no GitHub (campo "website" do repositório), no currículo e nos perfis de freela.
- Atualizar a imagem `docs/painel.png` se o painel tiver mudado.

**Pronto quando:** o link aparece no README e foi aberto num celular sem problema.

## Alternativa, se a etapa 3 der trabalho demais

Gerar o painel como **página estática**: a própria coleta diária exporta os dados em JSON e publica no GitHub Pages, como o Tumble Gems. Fica sempre no ar e não dorme, mas perde a API ao vivo (o `/docs` continua só no repositório).
