"""Testes do controle de validade dos documentos.

    python3 -m unittest discover -s cacador-licitacoes/tests
"""

import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import compliance  # noqa: E402

HOJE = dt.date(2026, 10, 16)


def doc(**kw):
    base = {"id": "x", "nome": "Doc", "onde": "", "validade_dias": None,
            "emitido_em": None, "vence_em": None}
    base.update(kw)
    return base


class ComplianceTest(unittest.TestCase):
    def test_status(self):
        casos = [
            (doc(), compliance.FALTANDO),
            (doc(emitido_em="2026-09-01", validade_dias=30), compliance.VENCIDO),
            (doc(emitido_em="2026-10-01", validade_dias=30), compliance.VENCENDO),
            (doc(emitido_em="2026-10-10", validade_dias=180), compliance.OK),
            (doc(emitido_em="2024-01-01"), compliance.PERMANENTE),
            # vence_em impresso na certidão tem prioridade sobre validade_dias
            (doc(emitido_em="2026-10-10", validade_dias=180, vence_em="2026-10-20"),
             compliance.VENCENDO),
        ]
        for d, esperado in casos:
            self.assertEqual(compliance.avaliar(d, HOJE, 15)[0], esperado, d)

    def test_estrito_e_relatorio(self):
        with tempfile.TemporaryDirectory() as tmp:
            arq = os.path.join(tmp, "docs.json")
            with open(arq, "w", encoding="utf-8") as f:
                json.dump({"documentos": [
                    doc(nome="CRF FGTS", emitido_em="2026-09-01", validade_dias=30),
                    doc(nome="Contrato social", emitido_em="2024-01-01")]}, f)
            saida = os.path.join(tmp, "rel.md")
            rc = compliance.main(["--arquivo", arq, "--hoje", "2026-10-16",
                                  "--saida", saida, "--estrito"])
            self.assertEqual(rc, 1)
            with open(saida, encoding="utf-8") as f:
                texto = f.read()
            self.assertIn("vencido há 15 dia(s)", texto)
            self.assertLess(texto.index("CRF FGTS"), texto.index("Contrato social"))

    def test_cadastro_padrao_valido(self):
        with open(os.path.join(os.path.dirname(compliance.__file__),
                               "compliance", "documentos.json"), encoding="utf-8") as f:
            docs = json.load(f)["documentos"]
        self.assertEqual(len({d["id"] for d in docs}), len(docs))
        self.assertEqual(compliance.main(["--hoje", "2026-10-16"]), 0)


if __name__ == "__main__":
    unittest.main()
