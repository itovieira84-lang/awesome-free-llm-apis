"""Testes offline: sobe um servidor local que imita a API de consulta do PNCP.

    python3 -m unittest discover -s cacador-licitacoes/tests
"""

import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cacador  # noqa: E402


def contratacao(seq, objeto, valor=50000.0, uf="SE"):
    return {
        "numeroControlePNCP": f"00000000000100-1-{seq:06d}/2026",
        "objetoCompra": objeto,
        "informacaoComplementar": None,
        "valorTotalEstimado": valor,
        "dataAberturaProposta": "2026-10-20T08:00:00",
        "dataEncerramentoProposta": f"2026-11-{seq:02d}T09:00:00",
        "modalidadeId": 6,
        "modalidadeNome": "Pregão - Eletrônico",
        "srp": False,
        "anoCompra": 2026,
        "sequencialCompra": seq,
        "linkSistemaOrigem": "https://exemplo.gov.br",
        "orgaoEntidade": {"cnpj": "00000000000100", "razaoSocial": "PREFEITURA DE TESTE"},
        "unidadeOrgao": {"ufSigla": uf, "municipioNome": "Aracaju"},
    }


PAGINAS = {
    1: [contratacao(1, "Contratação de agência de PUBLICIDADE para campanhas institucionais"),
        contratacao(2, "Aquisição de medicamentos para campanha de vacinação"),
        contratacao(3, "Curso de capacitação em liderança para servidores", 30000)],
    2: [contratacao(4, "Aquisição de pneus"),
        contratacao(1, "Contratação de agência de PUBLICIDADE para campanhas institucionais"),
        contratacao(5, "Limpeza de curso d'água e recursos hídricos")],
}


class FakePNCP(http.server.BaseHTTPRequestHandler):
    pedidos = []

    def do_GET(self):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        FakePNCP.pedidos.append(q)
        pagina = int(q["pagina"])
        corpo = json.dumps({"data": PAGINAS.get(pagina, []), "totalRegistros": 6,
                            "totalPaginas": len(PAGINAS), "numeroPagina": pagina}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *a):
        pass


class CacadorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), FakePNCP)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_busca_filtra_e_gera_relatorios(self):
        FakePNCP.pedidos.clear()
        with tempfile.TemporaryDirectory() as tmp:
            rc = cacador.main(["--base-url", self.base, "--uf", "SE", "--modalidade", "6",
                               "--saida", tmp, "--novas"])
            self.assertEqual(rc, 0)
            with open(os.path.join(tmp, "oportunidades.json"), encoding="utf-8") as f:
                ops = json.load(f)
            self.assertEqual([o["id_pncp"][-11:] for o in ops], ["000001/2026", "000003/2026"])
            self.assertEqual(ops[0]["areas"], "publicidade")
            self.assertEqual(ops[1]["areas"], "treinamento")
            self.assertTrue(ops[1]["faixa_me_epp"])
            self.assertEqual(ops[0]["link_pncp"],
                             "https://pncp.gov.br/app/editais/00000000000100/2026/1")
            self.assertTrue(os.path.exists(os.path.join(tmp, "oportunidades.csv")))
            with open(os.path.join(tmp, "oportunidades.md"), encoding="utf-8") as f:
                self.assertIn("PUBLICIDADE", f.read())
            self.assertEqual(FakePNCP.pedidos[0]["uf"], "SE")
            self.assertEqual(FakePNCP.pedidos[0]["codigoModalidadeContratacao"], "6")
            self.assertEqual(len(FakePNCP.pedidos), 2)

            # Segunda rodada com --novas: nada de novo.
            cacador.main(["--base-url", self.base, "--uf", "SE", "--modalidade", "6",
                          "--saida", tmp, "--novas"])
            with open(os.path.join(tmp, "oportunidades.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f), [])

    def test_palavra_no_inicio_da_palavra(self):
        grupos = {"t": cacador.compilar(["curso"])}
        self.assertIsNotNone(cacador.classificar("Cursos de Excel", grupos, []))
        self.assertIsNone(cacador.classificar("Gestão de recursos", grupos, []))


if __name__ == "__main__":
    unittest.main()
