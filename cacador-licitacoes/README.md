# Caçador de licitações · Nextgen Accelerator

Busca diária de licitações abertas no PNCP compatíveis com as atividades da **NEXTGEN ACCELERATOR LTDA** (CNPJ 51.186.218/0001-13, ME, Aracaju/SE):

- 73.11-4-00 · Agências de publicidade
- 85.99-6-04 · Treinamento em desenvolvimento profissional e gerencial

## Uso

```bash
python3 cacador-licitacoes/cacador.py            # SE, AL, BA e PE (ver empresa.json)
python3 cacador-licitacoes/cacador.py --brasil   # todas as UFs
python3 cacador-licitacoes/cacador.py --novas    # só o que é novo desde a última rodada
```

Só depende do Python 3 (sem bibliotecas externas). Os relatórios saem em `cacador-licitacoes/relatorios/`.

No GitHub, o workflow **Caçador de licitações** roda em dias úteis às 07h (Brasília); o relatório aparece no resumo da execução e como artifact. Para rodar na hora: Actions → Caçador de licitações → Run workflow.

## Arquivos

| Arquivo | Para quê |
|---------|----------|
| `empresa.json` | Dados da empresa, UFs, modalidades, palavras-chave e exclusões |
| `cacador.py` | Busca no PNCP e gera os relatórios |
| `CHECKLIST-HABILITACAO.md` | Documentos, certidões e atestados, com onde emitir e validade |
| `compliance.py` | Confere a validade das certidões cadastradas e avisa o que vence |
| `compliance/documentos.json` | Cadastro dos documentos: preencha a data de emissão ou validade |
| `compliance/PROGRAMA-INTEGRIDADE.md` | Rascunho do programa de integridade da empresa |
| `tests/` | Testes offline (`python3 -m unittest discover -s cacador-licitacoes/tests`) |

As skills do Claude ficam em `.claude/skills/`: `cacador-licitacoes`, `habilitacao-licitacoes`, `analise-edital` e `compliance-licitacoes`.
