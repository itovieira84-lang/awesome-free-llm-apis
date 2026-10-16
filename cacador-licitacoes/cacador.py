#!/usr/bin/env python3
"""Caçador de licitações: busca contratações com propostas abertas no PNCP
(Portal Nacional de Contratações Públicas) e filtra pelas atividades da empresa.

Usa só a biblioteca padrão do Python. Exemplos:

    python3 cacador.py                      # UFs do empresa.json
    python3 cacador.py --uf SE --uf AL      # só essas UFs
    python3 cacador.py --brasil             # todo o país (demora mais)
    python3 cacador.py --novas              # só o que ainda não foi visto

Saída em ./relatorios/: oportunidades.md, oportunidades.csv e oportunidades.json.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://pncp.gov.br/api/consulta"
PAGE_SIZE = 50  # máximo aceito pela API de consulta
PAUSA = 1.0  # segundos entre páginas; o PNCP devolve 429 se for rápido demais

MODALIDADES = {
    1: "Leilão eletrônico",
    2: "Diálogo competitivo",
    3: "Concurso",
    4: "Concorrência eletrônica",
    5: "Concorrência presencial",
    6: "Pregão eletrônico",
    7: "Pregão presencial",
    8: "Dispensa de licitação",
    9: "Inexigibilidade",
    10: "Manifestação de interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão presencial",
}

# Teto do art. 48, I, da LC 123/2006 para itens exclusivos de ME/EPP.
LIMITE_EXCLUSIVO_ME = 80_000

HERE = os.path.dirname(os.path.abspath(__file__))


def normalizar(texto):
    """Minúsculas, sem acentos e só letras/números separados por espaço."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", texto).split())


def compilar(termos):
    """Cada termo casa no início de palavra e aceita sufixo (curso -> cursos)."""
    return [(t, re.compile(r"\b" + re.escape(normalizar(t)))) for t in termos]


def classificar(texto, grupos, exclusoes):
    """Devolve {grupo: [termos encontrados]} ou None se o texto deve ser descartado."""
    norm = normalizar(texto)
    if any(rx.search(norm) for _, rx in exclusoes):
        return None
    achados = {}
    for grupo, termos in grupos.items():
        hits = [t for t, rx in termos if rx.search(norm)]
        if hits:
            achados[grupo] = hits
    return achados or None


def buscar_pagina(base_url, params, tentativas=6):
    url = f"{base_url}/v1/contratacoes/proposta?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "cacador-licitacoes/1.0"})
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 204:
                    return {"data": [], "totalPaginas": 0}
                corpo = resp.read()
                return json.loads(corpo) if corpo else {"data": [], "totalPaginas": 0}
        except urllib.error.HTTPError as e:
            if e.code == 204:
                return {"data": [], "totalPaginas": 0}
            if e.code < 500 and e.code != 429:
                detalhe = e.read().decode("utf-8", "replace")[:300]
                raise RuntimeError(f"PNCP recusou a consulta ({e.code}): {detalhe}") from e
            erro = e
            espera = e.headers.get("Retry-After") if e.code == 429 else None
            if espera and espera.isdigit():
                time.sleep(int(espera))
                continue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            erro = e
        time.sleep(min(60, 5 * 2 ** i))
    raise RuntimeError(f"PNCP indisponível após {tentativas} tentativas: {erro}")


def coletar(base_url, data_final, modalidades, ufs, max_paginas=None, log=print,
            pausa=PAUSA, falhas=None):
    """Itera todas as contratações com proposta aberta até data_final.

    Uma consulta que falha de vez vai para `falhas` e a busca segue com as outras.
    """
    for modalidade in modalidades:
        for uf in ufs or [None]:
            pagina = 1
            while True:
                if pagina > 1:
                    time.sleep(pausa)
                params = {"dataFinal": data_final,
                          "codigoModalidadeContratacao": modalidade,
                          "pagina": pagina, "tamanhoPagina": PAGE_SIZE}
                if uf:
                    params["uf"] = uf
                try:
                    resp = buscar_pagina(base_url, params)
                except RuntimeError as e:
                    nome = f"{MODALIDADES.get(modalidade, modalidade)} / {uf or 'Brasil'}"
                    log(f"  AVISO: {nome} parou na página {pagina}: {e}")
                    if falhas is not None:
                        falhas.append(f"{nome} (a partir da página {pagina})")
                    break
                dados = resp.get("data") or []
                total = resp.get("totalPaginas") or 0
                if pagina == 1:
                    log(f"  {MODALIDADES.get(modalidade, modalidade)} / {uf or 'Brasil'}: "
                        f"{resp.get('totalRegistros', len(dados))} abertas")
                yield from dados
                if not dados or pagina >= total or (max_paginas and pagina >= max_paginas):
                    break
                pagina += 1


def link_pncp(c):
    cnpj = (c.get("orgaoEntidade") or {}).get("cnpj")
    if cnpj and c.get("anoCompra") and c.get("sequencialCompra"):
        return f"https://pncp.gov.br/app/editais/{cnpj}/{c['anoCompra']}/{c['sequencialCompra']}"
    return c.get("linkSistemaOrigem") or ""


def resumir(c, achados):
    orgao = c.get("orgaoEntidade") or {}
    unidade = c.get("unidadeOrgao") or {}
    valor = c.get("valorTotalEstimado")
    return {
        "id_pncp": c.get("numeroControlePNCP"),
        "objeto": " ".join((c.get("objetoCompra") or "").split()),
        "orgao": orgao.get("razaoSocial"),
        "municipio": unidade.get("municipioNome"),
        "uf": unidade.get("ufSigla"),
        "modalidade": c.get("modalidadeNome") or MODALIDADES.get(c.get("modalidadeId"), ""),
        "valor_estimado": valor,
        "abertura_propostas": c.get("dataAberturaProposta"),
        "encerramento_propostas": c.get("dataEncerramentoProposta"),
        "srp": c.get("srp"),
        "areas": ", ".join(sorted(achados)),
        "termos": ", ".join(sorted({t for ts in achados.values() for t in ts})),
        "faixa_me_epp": bool(valor) and valor <= LIMITE_EXCLUSIVO_ME,
        "link_pncp": link_pncp(c),
        "link_sistema_origem": c.get("linkSistemaOrigem") or "",
    }


def filtrar(contratacoes, cfg):
    grupos = {g: compilar(ts) for g, ts in cfg["palavras_chave"].items()}
    exclusoes = compilar(cfg.get("palavras_excluir", []))
    busca = cfg.get("busca", {})
    vmin, vmax = busca.get("valor_minimo") or 0, busca.get("valor_maximo")
    vistos, saida = set(), []
    for c in contratacoes:
        cid = c.get("numeroControlePNCP")
        if cid in vistos:
            continue
        vistos.add(cid)
        valor = c.get("valorTotalEstimado") or 0
        if valor and (valor < vmin or (vmax and valor > vmax)):
            continue
        texto = f"{c.get('objetoCompra', '')} {c.get('informacaoComplementar') or ''}"
        achados = classificar(texto, grupos, exclusoes)
        if achados:
            saida.append(resumir(c, achados))
    saida.sort(key=lambda o: o["encerramento_propostas"] or "9999")
    return saida


def brl(v):
    if v in (None, ""):
        return "não informado"
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(iso):
    if not iso:
        return "-"
    try:
        return dt.datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def escrever_relatorios(oportunidades, pasta, cfg, novas_ids=None, falhas=None):
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, "oportunidades.json"), "w", encoding="utf-8") as f:
        json.dump(oportunidades, f, ensure_ascii=False, indent=2)
    if oportunidades:
        with open(os.path.join(pasta, "oportunidades.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(oportunidades[0]), delimiter=";")
            w.writeheader()
            w.writerows(oportunidades)

    emp = cfg["empresa"]
    hoje = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [f"# Oportunidades para {emp['nome_fantasia']}", "",
              f"Gerado em {hoje}. {len(oportunidades)} contratações com proposta aberta "
              f"casaram com as atividades da empresa.", ""]
    if falhas:
        linhas += ["> **Busca incompleta.** Estas consultas falharam no PNCP: "
                   + "; ".join(falhas) + ".", ""]
    for o in oportunidades:
        marca = " 🆕" if novas_ids and o["id_pncp"] in novas_ids else ""
        me = " · faixa exclusiva ME/EPP possível" if o["faixa_me_epp"] else ""
        linhas += [
            f"## {o['objeto'][:160]}{marca}", "",
            f"- **Órgão:** {o['orgao']} ({o['municipio']}/{o['uf']})",
            f"- **Modalidade:** {o['modalidade']}{' · registro de preços' if o['srp'] else ''}",
            f"- **Valor estimado:** {brl(o['valor_estimado'])}{me}",
            f"- **Propostas até:** {data_br(o['encerramento_propostas'])}",
            f"- **Área:** {o['areas']} (termos: {o['termos']})",
            f"- **Edital:** {o['link_pncp']}",
            "",
        ]
    with open(os.path.join(pasta, "oportunidades.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Caçador de licitações no PNCP")
    ap.add_argument("--config", default=os.path.join(HERE, "empresa.json"))
    ap.add_argument("--uf", action="append", help="UF a buscar (repita para várias)")
    ap.add_argument("--brasil", action="store_true", help="busca em todas as UFs")
    ap.add_argument("--modalidade", type=int, action="append",
                    help="código da modalidade (6 = pregão eletrônico, 8 = dispensa...)")
    ap.add_argument("--dias", type=int, help="propostas que encerram em até N dias")
    ap.add_argument("--max-paginas", type=int, help="limite de páginas por consulta")
    ap.add_argument("--saida", default=os.path.join(HERE, "relatorios"))
    ap.add_argument("--novas", action="store_true",
                    help="mostra só oportunidades ainda não vistas (usa vistos.json)")
    ap.add_argument("--pausa", type=float, default=PAUSA,
                    help="segundos entre páginas (padrão %(default)s)")
    ap.add_argument("--base-url", default=os.environ.get("PNCP_BASE_URL", BASE_URL))
    args = ap.parse_args(argv)

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    busca = cfg.get("busca", {})
    ufs = [] if args.brasil else (args.uf or busca.get("ufs") or [])
    modalidades = args.modalidade or busca.get("modalidades") or [6, 8]
    dias = args.dias or busca.get("dias_a_frente", 60)
    data_final = (dt.date.today() + dt.timedelta(days=dias)).strftime("%Y%m%d")

    log = lambda m: print(m, file=sys.stderr)
    log(f"Buscando no PNCP propostas abertas até {data_final} "
        f"({', '.join(ufs) if ufs else 'Brasil inteiro'})...")
    falhas = []
    brutas = coletar(args.base_url, data_final, modalidades, [u.upper() for u in ufs],
                     args.max_paginas, log, args.pausa, falhas)
    oportunidades = filtrar(brutas, cfg)

    novas_ids = None
    caminho_vistos = os.path.join(args.saida, "vistos.json")
    if args.novas:
        vistos = set()
        if os.path.exists(caminho_vistos):
            with open(caminho_vistos, encoding="utf-8") as f:
                vistos = set(json.load(f))
        novas_ids = {o["id_pncp"] for o in oportunidades} - vistos
        oportunidades = [o for o in oportunidades if o["id_pncp"] in novas_ids]
        os.makedirs(args.saida, exist_ok=True)
        with open(caminho_vistos, "w", encoding="utf-8") as f:
            json.dump(sorted(vistos | novas_ids), f)

    escrever_relatorios(oportunidades, args.saida, cfg, novas_ids, falhas)
    log(f"{len(oportunidades)} oportunidades. Relatório em {args.saida}/oportunidades.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
