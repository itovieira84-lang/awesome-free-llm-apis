---
name: cacador-licitacoes
description: Busca licitações abertas no PNCP compatíveis com a Nextgen Accelerator (publicidade e treinamento) e resume as melhores. Use para "caçar licitações", "tem edital novo?", "oportunidades de licitação".
---

# Caçador de licitações (PNCP)

O código fica em `cacador-licitacoes/`. O perfil da empresa, as UFs, as modalidades e as palavras-chave ficam em `cacador-licitacoes/empresa.json`.

## Como rodar

```bash
python3 cacador-licitacoes/cacador.py                 # UFs do empresa.json
python3 cacador-licitacoes/cacador.py --uf SE --uf BA # UFs específicas
python3 cacador-licitacoes/cacador.py --brasil        # país inteiro (lento)
python3 cacador-licitacoes/cacador.py --novas         # só o que ainda não foi visto
python3 cacador-licitacoes/cacador.py --modalidade 8  # só dispensas
```

Saída em `cacador-licitacoes/relatorios/` (`oportunidades.md`, `.csv`, `.json`). O GitHub Action `Caçador de licitações` roda em dias úteis às 07h e publica o relatório no resumo do job.

Se a rede deste ambiente bloquear `pncp.gov.br`, rode pelo Action (workflow_dispatch) e leia o artifact `oportunidades`.

## API usada

`GET https://pncp.gov.br/api/consulta/v1/contratacoes/proposta` com `dataFinal` (AAAAMMDD), `codigoModalidadeContratacao`, `uf`, `pagina`, `tamanhoPagina` (10 a 50). Modalidades: 4 concorrência eletrônica, 6 pregão eletrônico, 7 pregão presencial, 8 dispensa, 12 credenciamento, 3 concurso. Link público do edital: `https://pncp.gov.br/app/editais/{cnpjOrgao}/{anoCompra}/{sequencialCompra}`.

## Ao apresentar resultados

1. Ordene por prazo de encerramento das propostas; descarte os que encerram em menos de 3 dias úteis, salvo dispensas.
2. Para cada oportunidade: objeto em uma linha, órgão e cidade, valor, prazo, link.
3. Destaque o que cabe na faixa exclusiva de ME/EPP (até R$ 80 mil).
4. Lembre que licitação de agência de publicidade pela Lei 12.232/2010 exige o certificado do CENP; pregões de redes sociais, design e vídeo normalmente não.
5. Para triagem de um edital específico, use a skill `analise-edital`; para documentos, `habilitacao-licitacoes`.

## Ajustes

Falso positivo recorrente → adicionar termo em `palavras_excluir`. Área nova de atuação → novo grupo em `palavras_chave`. Termos são comparados sem acento e no início de palavra (`curso` casa `cursos`, não `recurso`).
