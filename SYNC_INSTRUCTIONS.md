# Sincronização Notion → Dashboard (Monet Comercial)

Este dashboard é um HTML estático (sem build). Os dados vêm da base Notion
**"Carteira de ECs — Monet"** (data source `6871d356-b658-4178-ac08-43da5ba5bd86`)
e da base **"🚨 Alertas & Pedidos da Diretoria"** (data source `7ec6a154-5d77-4d0e-8008-90057fdbb26b`),
ambas dentro da página "Monet — Central de Vendas" no Notion.

## Passo a passo (rodar 2x ao dia via tarefa agendada)

1. **Consultar a base "Carteira de ECs — Monet" via `mcp__Notion__notion-query-data-sources`** (modo SQL),
   usando exatamente esta query (pagine com `LIMIT 100 OFFSET N` até `has_more:false`):

   ```sql
   SELECT url, "Estabelecimento", "Consultor", "Etapa", "Meta TPV",
          "date:Data de Cadastro:start" as data_cad, "CNPJ/CPF",
          "Situação POS (planilha)", "Situação FiServ (planilha)",
          "Status Original (planilha)", "Telefone", "Observação",
          "Código Planilha", "Segmento / Nicho", "Categoria de Prospecção"
   FROM "collection://6871d356-b658-4178-ac08-43da5ba5bd86"
   ```

   Descarte linhas onde `"Estabelecimento"` é nulo. Salve o resultado combinado como uma lista JSON
   (mesmo formato retornado pela tool) em `dataset.json`.

2. **Consultar a base de Alertas** (apenas os não resolvidos):

   ```sql
   SELECT "Estabelecimento / Assunto", "Categoria", "Consultor", "Descrição",
          "Prioridade", "date:Data:start" as data
   FROM "collection://7ec6a154-5d77-4d0e-8008-90057fdbb26b"
   WHERE "Resolvido" IS NULL OR "Resolvido" = '__NO__'
   ```

   Salve como `alertas.json` (lista de objetos com essas chaves). Se vazio, use `[]`.

3. **Gerar o novo `index.html`:**

   ```bash
   python3 generate_dashboard.py dataset.json alertas.json index.html > index_new.html
   mv index_new.html index.html
   ```

   O script preserva todo o CSS/estrutura existente e substitui apenas: os arrays `ECS`/`PROSP`,
   a lista `GRUPOS` (Etapas), as cores de consultores, o bloco "Situação (Diretoria)", o cálculo de
   fechamento do mês e o carimbo de "sincronizado em".

   IMPORTANTE: o campo "Meta TPV" no Notion é digitado em **milhares** (ex: 125 = R$125 mil) —
   o script já multiplica por 1000. Não duplique essa conversão na consulta.

4. **Commit e push:**

   ```bash
   git add index.html
   git commit -m "sync: atualiza dashboard a partir do Notion ($(date -u +%Y-%m-%dT%H:%MZ))"
   git push
   ```

   Só faça commit se `git diff --stat index.html` mostrar mudanças reais (evita commits vazios).

## Limitações conhecidas (não tentar "consertar" automaticamente)

- **Segmento / Nicho** e **Categoria de Prospecção**: só existem no Notion a partir de 16/08/2026.
  Registros sem esses campos preenchidos aparecem como "Não categorizado" — isso é esperado, não é bug.
- A aba "Situação (Diretoria)" combina cálculos automáticos (Recusados, Erros, Em Análise) com itens da
  base de Alertas. Se a base de Alertas estiver vazia, a seção 5 mostra um aviso pedindo para o time
  cadastrar os itens lá — isso é esperado.
