---
name: compliance-licitacoes
description: Controla a validade das certidões e documentos da Nextgen Accelerator e orienta o programa de integridade (compliance). Use para "certidões vencendo", "estou apta a licitar?", "atualizar certidão", "programa de integridade".
---

# Compliance para licitações

## Controle de validade

O cadastro fica em `cacador-licitacoes/compliance/documentos.json`. Para cada documento emitido, preencha `emitido_em` (AAAA-MM-DD) e, se a certidão trouxer a data de validade, `vence_em`. A data em `vence_em` vale mais que `validade_dias`.

```bash
python3 cacador-licitacoes/compliance.py            # relatório
python3 cacador-licitacoes/compliance.py --dias 30  # alerta com 30 dias
python3 cacador-licitacoes/compliance.py --estrito  # erro se houver vencido/faltando
```

O workflow diário do caçador inclui este relatório no resumo da execução.

Ao atualizar uma certidão a pedido do usuário: edite só a entrada correspondente, rode o relatório e mostre o que ainda está pendente. Nunca invente datas; peça a data de emissão ou a validade impressa.

## Antes de entrar em um edital

Rode o relatório e cruze com a seção de habilitação do edital (skill `habilitacao-licitacoes`). Um documento que vence antes da data da sessão conta como vencido.

## Programa de integridade

O rascunho está em `cacador-licitacoes/compliance/PROGRAMA-INTEGRIDADE.md`. Ele serve de desempate (Lei 14.133, art. 60, IV) e pode ser exigido em contratos de grande vulto (art. 25, §4º). Ao revisar, mantenha proporcional a uma microempresa.
