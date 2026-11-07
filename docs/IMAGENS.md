# Evidências visuais e origem das imagens

Todos os PNGs abaixo são **capturas de tela compartilhadas durante o desenvolvimento** e não imagens geradas, recriações ou mockups. O diagrama em `assets/diagrams/arquitetura.svg` é **ilustrativo**, não um screenshot.

## V9.3 — painel real em funcionamento

| Arquivo | Conteúdo | Interpretação correta |
|---|---|---|
| `08-v93-painel-real.png` | Topo do painel roxo, métricas, status, narrativas | Captura de sessão de **16/10/2026, 14:48 BRT**, com ordens reais desativadas. Banca US$ 1.000 fictícios, P&L −US$ 44,62, 161 tokens registrados, 0 narrativas. |
| `09-v93-microcaps-reais.png` | Tabela de tokens com MC, FDV, liquidez, atividade e risco/dados | Parcela da interface em execução, **não** prova que todos os tokens estavam disponíveis para negociação. |
| `10-v93-operacoes-reais.png` | Tabela com posição aberta, stops e token clicável | **Operações fictícias**. A coluna P&L não é histórico de transações reais. |

Essas capturas pertencem à mesma versão, mas não há evidência de que todas foram capturadas exatamente no mesmo segundo. Mostram o programa já com dados, não uma inicialização vazia. Também não demonstram entrega de notificação do Windows ou reprodução do som.

## Histórico de versões anteriores

| Arquivo | Versão | Uso adequado |
|---|---|---|
| `01-v3-monitor.png` | V3 | Evolução do monitor |
| `02-v4-paper-trading.png` | V4 | Primeiras operações simuladas |
| `03-v5-filtros.png` | V5 | Critérios e rejeições |
| `04-v7-mc-fdv.png` | V7 | MC/FDV e histórico simulado |
| `05-v91-microcaps.png` | V9.1 | Descoberta inicial de microcaps |
| `06-v92-auditoria.png` | V9.2 | Cotação e saída auditadas |
| `07-v92-operacoes.png` | V9.2 | Operações anteriores à V9.3 |

**Não apresentar essas sete capturas como se fossem o painel da V9.3.** Seus dados são amostras históricas e simuladas.

## O que falta como evidência

- [ ] Notificação do Windows realmente entregue, incluindo comprovação manual do som.
- [ ] Avaliação reproduzível com dados de mercado gravados, sem vazamento temporal.
- [ ] Auditoria independente de liquidez e segurança on-chain.
- [ ] Cobertura independente da Robinhood Chain.

Antes de fazer o repositório público, revisar novamente cada imagem para garantir que não haja credenciais ou dados pessoais visíveis.
