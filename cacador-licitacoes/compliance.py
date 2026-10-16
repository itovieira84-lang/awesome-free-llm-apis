#!/usr/bin/env python3
"""Compliance de habilitação: confere a validade das certidões e documentos
cadastrados em compliance/documentos.json e avisa o que falta ou vai vencer.

    python3 compliance.py                 # relatório no terminal
    python3 compliance.py --dias 30       # janela de alerta de 30 dias
    python3 compliance.py --saida rel.md  # grava o relatório em Markdown
    python3 compliance.py --estrito       # sai com erro se algo estiver vencido ou faltando
"""

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

FALTANDO, VENCIDO, VENCENDO, OK, PERMANENTE = (
    "faltando", "vencido", "vencendo", "ok", "sem validade")
ORDEM = {VENCIDO: 0, FALTANDO: 1, VENCENDO: 2, OK: 3, PERMANENTE: 4}
ICONE = {VENCIDO: "🔴", FALTANDO: "⚪", VENCENDO: "🟡", OK: "🟢", PERMANENTE: "🟢"}


def data(valor):
    return dt.date.fromisoformat(valor) if valor else None


def avaliar(doc, hoje, janela):
    """Devolve (status, data de vencimento ou None, dias restantes ou None)."""
    emitido = data(doc.get("emitido_em"))
    vence = data(doc.get("vence_em"))
    if not vence and emitido and doc.get("validade_dias"):
        vence = emitido + dt.timedelta(days=doc["validade_dias"])
    if not emitido and not vence:
        return FALTANDO, None, None
    if not vence:
        return PERMANENTE, None, None
    restam = (vence - hoje).days
    if restam < 0:
        return VENCIDO, vence, restam
    if restam <= janela:
        return VENCENDO, vence, restam
    return OK, vence, restam


def relatorio(docs, hoje, janela):
    linhas_aval = []
    for d in docs:
        status, vence, restam = avaliar(d, hoje, janela)
        linhas_aval.append((ORDEM[status], restam if restam is not None else 99999, d, status, vence, restam))
    linhas_aval.sort(key=lambda t: (t[0], t[1]))

    contagem = {}
    for *_, status, _v, _r in linhas_aval:
        contagem[status] = contagem.get(status, 0) + 1
    aptos = not contagem.get(VENCIDO) and not contagem.get(FALTANDO)

    out = [f"# Compliance de habilitação ({hoje.strftime('%d/%m/%Y')})", "",
           ("**Pronta para licitar:** todos os documentos em dia." if aptos else
            f"**Pendências:** {contagem.get(VENCIDO, 0)} vencido(s), "
            f"{contagem.get(FALTANDO, 0)} faltando, {contagem.get(VENCENDO, 0)} vencendo "
            f"em até {janela} dias."), "",
           "| | Documento | Situação | Vence em | Onde emitir |",
           "|---|---|---|---|---|"]
    for *_, d, status, vence, restam in linhas_aval:
        if status == VENCENDO:
            situacao = f"vence em {restam} dia(s)"
        elif status == VENCIDO:
            situacao = f"vencido há {-restam} dia(s)"
        else:
            situacao = status
        out.append(f"| {ICONE[status]} | {d['nome']} | {situacao} | "
                   f"{vence.strftime('%d/%m/%Y') if vence else '-'} | {d.get('onde', '')} |")
    return "\n".join(out) + "\n", aptos


def main(argv=None):
    ap = argparse.ArgumentParser(description="Confere a validade dos documentos de habilitação")
    ap.add_argument("--arquivo", default=os.path.join(HERE, "compliance", "documentos.json"))
    ap.add_argument("--dias", type=int, default=15, help="janela de alerta (padrão 15 dias)")
    ap.add_argument("--hoje", help="data de referência AAAA-MM-DD (para testes)")
    ap.add_argument("--saida", help="grava o relatório neste arquivo")
    ap.add_argument("--estrito", action="store_true",
                    help="código de saída 1 se houver documento vencido ou faltando")
    args = ap.parse_args(argv)

    with open(args.arquivo, encoding="utf-8") as f:
        docs = json.load(f)["documentos"]
    hoje = data(args.hoje) or dt.date.today()
    texto, aptos = relatorio(docs, hoje, args.dias)
    if args.saida:
        os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
        with open(args.saida, "w", encoding="utf-8") as f:
            f.write(texto)
    print(texto)
    return 1 if args.estrito and not aptos else 0


if __name__ == "__main__":
    sys.exit(main())
