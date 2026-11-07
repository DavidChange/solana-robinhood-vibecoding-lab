# Decisões de arquitetura (ADRs resumidas)

## ADR-001 — Python local + arquivos .BAT
**Contexto:** ambiente Windows e desenvolvimento incremental. **Decisão:** Python 3.13, scripts `.bat` e biblioteca padrão quando possível. **Limite:** não é infraestrutura de baixa latência e depende do computador estar ligado.

## ADR-002 — DEX Screener HTTP para protótipo
**Decisão:** REST/HTTP e consultas periódicas. **Motivo:** simplicidade de integração. **Limite:** cobertura parcial, dados agregados, potencial atraso e não há WebSocket de execução/ordens no projeto.

## ADR-003 — SQLite para trilha local
**Decisão:** banco local para posições, observações e eventos. **Motivo:** persistência e auditoria. **Lição:** cópia de banco e migração de schema requerem cuidado; os arquivos WAL/SHM podem conter dados em trânsito.

## ADR-004 — Paper trading obrigatório
**Decisão:** nenhuma chave de carteira, assinatura ou execução real. **Motivo:** validar fluxo sem risco financeiro direto. **Limite:** preço cotado não equivale a preço executado.

## ADR-005 — Separar MC de FDV
**Decisão:** armazenar/exibir métricas separadamente quando disponíveis. **Motivo:** não confundir oferta circulante com avaliação totalmente diluída. **Limite:** ambos podem coincidir; a exatidão depende da fonte.

## ADR-006 — RSS/watchlist em vez de X pago
**Decisão:** desabilitar X pago após erro 402 e escolha de não gastar. **Motivo:** protótipo gratuito. **Limite:** links sociais e correspondência por palavras-chave não fazem leitura inteligente do X.

## ADR-007 — Cotação auditável
**Decisão:** registrar preço, fonte, horário e liquidez de entrada/monitoramento/saída. **Motivo:** um lucro fictício da V9.1 não era reproduzível a partir do histórico regular. **Limite:** ainda não há cotação real de roteamento de swap.
