# Limitações conhecidas

1. O scanner usa uma amostra pública do DEX Screener, não um feed exaustivo de lançamento no primeiro bloco.
2. Tokens apresentados como Robinhood Chain seguem classificação dos dados consultados; não há prova independente de cobertura integral da rede.
3. MC e FDV dependem dos dados da API; igualdade não comprova circulação integral.
4. Liquidez informada em USD não equivale a profundidade executável para ordens específicas.
5. Stop, alvo, slippage e taxas são regras hipotéticas aplicadas a preços consultados; podem falhar em mercados reais.
6. Risco/atividade de bots são heurísticas, não detector confiável de fraude, honeypot ou coordenação entre carteiras.
7. Narrativas são manualmente cadastradas ou obtidas via RSS opcional; correspondência textual não valida associação oficial ao contrato.
8. Jev/AgenKit aparecem como inspiração inicial, mas **não estão integrados** ao código entregue.
9. A V9.3 foi executada no Windows e o painel roxo foi registrado em capturas reais; as notificações do Windows e o som, porém, não têm confirmação registrada.
10. Não há backtest histórico independente nem WebSocket de execução nesta implementação.
