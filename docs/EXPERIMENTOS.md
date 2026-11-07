# Experimentos citados na conversa

**Todos os valores abaixo são de operações fictícias/paper trading, não de lucros reais.** Amostras de diferentes versões não devem ser somadas ou tratadas como comparações controladas.

| Versão/amostra | Resultado registrado no histórico | Interpretação |
|---|---|---|
| V4, 6 operações | P&L −US$ 2,00 | Score alto sozinho não protege de quedas |
| V5, 6 operações | P&L +US$ 3,32 | Amostra pequena, insuficiente para inferência |
| V7, 5 operações | P&L −US$ 66,68 | 1 vencedora / 4 perdedoras no print analisado |
| V9.1, DacityCoin | +US$ 129,55 | Cotação de saída não constava no histórico regular — auditoria insuficiente |
| V9.2, 19 operações | P&L −US$ 20,82 | 2 vencedoras, 17 perdedoras na amostra enviada |

## O que falta para avaliação séria

- Dados de mercado coletados com timestamps e proveniência verificável.
- Replay que não utilize dados posteriores para tomar decisões passadas.
- Validação da capacidade real de venda por cotação de roteamento e liquidez do pool.
- Comparação de baselines no mesmo conjunto de dados com períodos fora da amostra de ajuste.
- Métricas de perda máxima, distribuição de retornos e incerteza estatística.

Não apresentar números acima como resultado de backtest comprovado nem promessa de rentabilidade.
