# Brief de design do painel

Referência para qualquer mudança visual no painel (`GET /`, arquivo [`src/indicadores/pagina.html`](../src/indicadores/pagina.html)). Mudança que contrarie este documento: atualize o documento junto, ou não faça.

## Para quem e para quê

- **Quem abre:** recrutador ou cliente vendo o portfólio, e qualquer pessoa curiosa sobre economia. Não é analista financeiro.
- **Tarefa principal:** saber o valor atual dos indicadores e ver como eles andaram. Tem que dar certo **sem ler instrução**.
- **Teste dos 5 segundos:** quem nunca viu entende que são indicadores do Banco Central, vê os 5 valores atuais e percebe que dá para clicar num deles.

## Fluxo

```
abre a página
  → cartões com o valor atual de cada indicador
  → gráfico do primeiro (dólar), último ano
clica num cartão  → o gráfico troca para ele, o período escolhido continua
clica num período → o gráfico do indicador atual é recarregado
clica em "Tema escuro" → troca claro/escuro (gráfico junto) e lembra a escolha
rodapé            → última coleta, documentação da API (/docs), código no GitHub, fonte
```

Uma tela só, sem navegação e sem rolagem no computador.

## Identidade

- **Tom:** sóbrio, de dado público. Sem efeito, sem gradiente, sem emoji. Quem chama a atenção é o número.
- **Cores:** definidas em variáveis CSS: claro no `:root`, escuro em `:root[data-theme="dark"]` (cada paleta escrita uma vez só).
- **Tema claro/escuro:** um script curto no `<head>` decide o tema antes de desenhar a página (para não piscar): vale a escolha salva no navegador (`localStorage`, chave `tema`, valores `light`/`dark`); sem escolha, o tema do sistema. Se o sistema trocar com a página aberta e não houver escolha salva, a página acompanha. Leitura e escrita do `localStorage` ficam em `try/catch`: se o navegador bloquear, o botão funciona até recarregar.

| Variável | Claro | Escuro | Uso |
| --- | --- | --- | --- |
| `--fundo` | `#f6f7fb` | `#0f141c` | fundo da página |
| `--cartao` | `#ffffff` | `#171e29` | cartões e painel do gráfico |
| `--texto` | `#1d2330` | `#e6ebf2` | texto principal e valores |
| `--suave` | `#5f6b7d` | `#93a0b4` | rótulos, datas, resumo |
| `--borda` | `#e2e6ef` | `#263040` | bordas e grade do gráfico |
| `--destaque` | `#1f6feb` | `#5b9dff` | seleção, linha do gráfico, links |
| `--destaque-fundo` | `#e8f0fe` | `#1b2a42` | cartão selecionado |
| `--sobre-destaque` | `#ffffff` | `#0f141c` | texto em cima da cor de destaque (botão de período ativo). No escuro é escuro porque branco sobre `#5b9dff` não passa no contraste |
| `--destaque-apagado` | `#628fee` | `#3f70ba` | barras anteriores à última nas séries mensais. Contraste com o cartão acima de 3:1 (3,1 no claro, 3,4 no escuro), o mínimo para elemento gráfico |

Cor nova só entra como variável, nas duas versões. Nada de cor solta no meio do CSS.

- **Fonte:** a do sistema (`Segoe UI`, `system-ui`). Sem fonte externa.
- **Tamanhos:** título 28, valor do cartão 24, título do gráfico 18, texto 14–16, rótulo 12–13.
- **Espaçamento:** múltiplos de 4 (4, 8, 12, 16, 24, 32). Cantos arredondados de 12 px nos blocos e 8 px nos botões.
- **Foco do teclado:** contorno de 2 px na cor de destaque em botões e links (`:focus-visible`).

## Componentes

- **Botão de tema:** no topo, à direita do título "Indicadores BR". Texto "Tema escuro" com ícone de lua; é um interruptor (`aria-pressed="true"` quando o escuro está ligado), com o mesmo visual de ligado do cartão selecionado (borda e fundo de destaque). Altura mínima de 40 px.
- **Cartão de indicador:** um `<button>` (dá para usar com o teclado) com nome curto (Dólar, Selic, CDI, IPCA, IGP-M), o que é em poucas palavras (ex.: "inflação oficial"), valor e data de referência. No valor, o número é grande e a unidade menor e em cor suave. Selecionado = borda e fundo de destaque e `aria-pressed="true"`.
- **Textos de explicação:** ficam no objeto `SOBRE` no começo do `<script>` da página (`curto` vai no cartão, `longo` embaixo do título do gráfico). Indicador novo sem entrada ali usa o nome da API.
- **Botões de período:** 1 mês, 6 meses, 1 ano, 5 anos, Tudo. O ativo fica preenchido com a cor de destaque e tem `aria-pressed="true"` (o CSS pinta pelo atributo, então visual e leitor de tela nunca discordam). Altura mínima de 40 px (toque). No celular ficam os 5 numa linha.
- **Séries mensais (IPCA, IGP-M):** o período conta meses a partir do último mês publicado: "1 ano" = 12 barras, "1 mês" = a última barra.
- **Título do gráfico:** o mesmo nome curto do cartão (Dólar, Selic, CDI, IPCA, IGP-M), vindo do `SOBRE.nome`; só a página muda, a API continua devolvendo o nome técnico. Embaixo, a frase do `SOBRE.longo` diz o que é para quem não é da área e guarda o detalhe técnico para quem entende (dólar: cotação de venda, PTAX; Selic: Meta Selic; CDI: anualizado).
- **Gráfico:** linha para série diária, barra para mensal (cada barra é um mês, não uma tendência contínua). Sem legenda; o título já diz o que é. Rótulos do eixo X sempre na horizontal (no celular, menos rótulos).
- **Valor mais recente no gráfico:** aparece sem passar o mouse (no celular não existe "passar o mouse").
  - Linha: um ponto no fim (raio 5, anel de 2 px na cor do cartão) e um rótulo com o valor curto ("R$ 5,0096", "13,75%"); a unidade completa está no cartão.
  - Barras: a última barra na cor de destaque, as anteriores em `--destaque-apagado`, e o rótulo na ponta da última barra (acima se positiva, abaixo se negativa).
  - O rótulo é um plugin próprio no `<script>` (`rotuloFinal`, sem biblioteca extra): caixinha com fundo do cartão, borda `--borda`, texto `--texto`, alinhada pela direita com o último ponto. Na linha, ele tenta posições de perto para longe (acima antes de abaixo) e fica na primeira que não cobre a linha; quando fica longe do ponto, um fio fino liga os dois.
  - O texto alternativo do gráfico começa pelo valor mais recente e a data dele.
  - O gráfico é canvas: ao trocar o tema ele é redesenhado para pegar as cores novas.
- **Resumo abaixo do gráfico:** começa pelo que mais interessa no período (variação para o dólar; "foi de X para Y" para Selic e CDI; acumulado para IPCA e IGP-M), depois mínimo, máximo e quantidade ("12 meses", "251 valores diários").

## Formato dos números

- Padrão brasileiro: `R$ 5,0096`, `15,00% ao ano`, `0,48% no mês`, datas `13/10/2026`.
- A API devolve a unidade abreviada (`% a.a.`); a página escreve por extenso ("ao ano") pelo objeto `UNIDADE` no `<script>`. **Decidido: a API não muda** (trocar na origem quebraria a página e quem já usa a API).
- Dólar com 4 casas (é como o Banco Central publica); o resto com 2.
- Série mensal mostra "referência 09/2026"; diária mostra "em 13/10/2026".

## Estados

| Estado | O que aparece |
| --- | --- |
| Carregando a página | "Carregando..." no lugar dos cartões |
| Indicador sem dado | valor "—" e "sem dados ainda" |
| Período sem dado | "Sem dados neste período." no meio do gráfico e "Sem dados no período." no resumo |
| Falha ao carregar a página | mensagem no lugar dos cartões e botão "Tentar de novo"; o painel do gráfico some |
| Trocando indicador ou período | título e explicação trocam na hora; o gráfico antigo fica apagado e o resumo diz "Carregando..."; se passar de 0,3 s, aparece "Carregando..." no meio do gráfico |
| Falha ao trocar indicador ou período | no lugar do gráfico: "Não foi possível carregar o histórico de X." e botão "Tentar de novo" |
| Falha só na última coleta | os cartões e o gráfico continuam; só a linha "Última coleta" do rodapé não aparece |

Clique rápido em vários cartões: só a resposta do último clique é desenhada.

## Tamanhos de tela

- **Computador (1280):** os 5 cartões numa linha.
- **Tablet (até 900):** cartões em 3 + 2, os dois de baixo dividindo a linha inteira.
- **Celular (até 560):** cartões em 2 + 2 + 1, o último ocupando a linha inteira; botões de período abaixo do título, os 5 na mesma linha. Sem rolagem horizontal.
- A divisão 3 + 2 e 2 + 2 + 1 conta com 5 indicadores (`nth-child` no CSS). Se entrar um sexto, revisar.

## Decisões já tomadas (revisão de 13/10/2026)

- ~~Título do gráfico com o nome da API~~ → nome curto só na página; a API não muda (ver "Título do gráfico").
- ~~Trocar `% a.a.` por "% ao ano" na origem~~ → recusado: fica abreviado na API; a página escreve por extenso.
- ~~Destacar o valor mais recente no gráfico~~ → ponto no fim da linha, última barra destacada e rótulo fixo com o valor (ver "Valor mais recente no gráfico").
- ~~Botão claro/escuro~~ → feito; padrão segue o sistema e a escolha fica salva no navegador (ver "Tema claro/escuro").

## Pontos em aberto (para a próxima revisão de design)

- Nenhum no momento.
