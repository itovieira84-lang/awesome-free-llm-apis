---
name: analise-edital
description: Lê um edital de licitação e faz a triagem vai/não vai para a Nextgen Accelerator, com prazos, exigências e riscos. Use quando receber um edital, link do PNCP ou termo de referência.
---

# Análise de edital (vai / não vai)

Entrada: PDF do edital, link do PNCP (`pncp.gov.br/app/editais/...`) ou o número de controle PNCP.
Os arquivos de um edital no PNCP saem em `https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos`.

## Extraia, nesta ordem

1. **Objeto** em uma frase e se é publicidade pela Lei 12.232/2010 (exige CENP e proposta técnica) ou serviço comum.
2. **Datas**: limite de propostas, impugnação e esclarecimentos (até 3 dias úteis antes), sessão.
3. **Plataforma** onde a disputa acontece e se a empresa já está cadastrada.
4. **Critério de julgamento** (menor preço, técnica e preço, maior desconto) e modo de disputa.
5. **Valor estimado** e se há itens exclusivos ou cota reservada para ME/EPP.
6. **Habilitação**: compare com `cacador-licitacoes/CHECKLIST-HABILITACAO.md` e liste só o que falta.
7. **Execução**: local (presencial fora de Aracaju pesa no custo), prazos, equipe mínima, garantia contratual, forma de pagamento.
8. **Riscos**: exigências que restringem a competição (podem ser impugnadas), multas altas, atestados com quantitativo acima de 50%.

## Resultado

Responda com: decisão (vai / não vai / vai se...), os 3 motivos principais, o que falta providenciar com prazo, e a data limite de impugnação se houver cláusula questionável.
