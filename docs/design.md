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
rodapé            → última coleta, documentação da API (/docs), código no GitHub, fonte
```

Uma tela só, sem navegação e sem rolagem no computador.

## Identidade

- **Tom:** sóbrio, de dado público. Sem efeito, sem gradiente, sem emoji. Quem chama a atenção é o número.
- **Cores:** definidas em variáveis CSS no `:root`, com versão escura em `prefers-color-scheme: dark`.

| Variável | Claro | Escuro | Uso |
| --- | --- | --- | --- |
| `--fundo` | `#f6f7fb` | `#0f141c` | fundo da página |
| `--cartao` | `#ffffff` | `#171e29` | cartões e painel do gráfico |
| `--texto` | `#1d2330` | `#e6ebf2` | texto principal e valores |
| `--suave` | `#5f6b7d` | `#93a0b4` | rótulos, datas, resumo |
| `--borda` | `#e2e6ef` | `#263040` | bordas e grade do gráfico |
| `--destaque` | `#1f6feb` | `#5b9dff` | seleção, linha do gráfico, links |
| `--destaque-fundo` | `#e8f0fe` | `#1b2a42` | cartão selecionado |

Cor nova só entra como variável, nas duas versões. Nada de cor solta no meio do CSS.

- **Fonte:** a do sistema (`Segoe UI`, `system-ui`). Sem fonte externa.
- **Tamanhos:** título 28, valor do cartão 24, título do gráfico 18, texto 14–16, rótulo 12–13.
- **Espaçamento:** múltiplos de 4 (4, 8, 12, 16, 24, 32). Cantos arredondados de 12 px nos blocos e 8 px nos botões.

## Componentes

- **Cartão de indicador:** um `<button>` (dá para usar com o teclado) com nome, valor e data de referência. Selecionado = borda e fundo de destaque.
- **Botões de período:** 1 mês, 6 meses, 1 ano, 5 anos, Tudo. O ativo fica preenchido com a cor de destaque.
- **Gráfico:** linha para série diária, barra para mensal (cada barra é um mês, não uma tendência contínua). Sem legenda; o título já diz o que é.
- **Resumo abaixo do gráfico:** quantidade de valores, mínimo e máximo; variação no período para o dólar; acumulado no período para IPCA e IGP-M.

## Formato dos números

- Padrão brasileiro: `R$ 5,0096`, `15,00% a.a.`, `0,48% no mês`, datas `13/10/2026`.
- Dólar com 4 casas (é como o Banco Central publica); o resto com 2.
- Série mensal mostra "referência 09/2026"; diária mostra "em 13/10/2026".

## Estados

| Estado | O que aparece |
| --- | --- |
| Carregando a página | "Carregando..." no lugar dos cartões |
| Indicador sem dado | valor "—" e "sem dados ainda" |
| Período sem dado | "Sem dados no período." no resumo |
| Falha ao carregar | mensagem no lugar dos cartões dizendo que não foi possível carregar |

## Tamanhos de tela

- **Computador (1280):** os 5 cartões numa linha.
- **Tablet (768) e celular (390):** os cartões quebram em linhas; os botões de período quebram abaixo do título. Sem rolagem horizontal.

## Pontos em aberto (para a próxima revisão de design)

- Trocar de indicador ou de período não mostra que está carregando, e uma falha nessa hora não aparece na tela.
- Os botões de período não informam ao leitor de tela qual está ativo (`aria-pressed`).
- "% a.a." pode não ser claro para quem não é da área; avaliar "% ao ano" nos cartões e no gráfico.
- Não há explicação curta do que é cada indicador (ex.: "IPCA: inflação oficial").
