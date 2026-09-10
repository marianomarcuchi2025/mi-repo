"""Tests unitarios del parser."""
from datetime import date
from pathlib import Path
import pytest
import parser
from parser import (
    Extraccion, _add_aviso, _enriquecer_gde, _norm, _primer_match,
    detectar_orden, detectar_termino, extraer, partir_numero_gde,
    pide_difusion,
)


class TestNorm:
    @pytest.mark.parametrize("entrada,esperado", [
        ("IF-2024-123.pdf", "IF2024123PDF"),
        ("if_2024_123", "IF2024123"),
        ("", ""),
        ("...---///", ""),
    ])
    def test_norm(self, entrada, esperado):
        assert _norm(entrada) == esperado


class TestAddAviso:
    def test_agrega(self, datos):
        _add_aviso(datos, "hola")
        assert datos.avisos == ["hola"]

    def test_no_duplica(self, datos):
        _add_aviso(datos, "x")
        _add_aviso(datos, "x")
        assert datos.avisos == ["x"]


class TestPrimerMatch:
    def test_primer_hit(self):
        r = _primer_match(lambda x: "HIT" if "hit" in x else None, "sin", "esto hit")
        assert r == "HIT"

    def test_ignora_vacios(self):
        llamadas = []
        def d(x):
            llamadas.append(x)
            return None
        _primer_match(d, None, "", "texto")
        assert llamadas == ["texto"]

    def test_sin_matches(self):
        assert _primer_match(lambda x: None, "a", "b") is None


class TestPartirNumeroGDE:
    def test_valido(self):
        p, n, s = partir_numero_gde("IF-2024-12345678-APN-ABC")
        assert (p, n, s) == ("IF", "2024-12345678", "APN-ABC")

    def test_sin_sufijo(self):
        p, n, s = partir_numero_gde("IF-2024-1234")
        assert (p, n, s) == ("IF", "2024-1234", "")

    def test_invalido(self):
        with pytest.raises(ValueError):
            partir_numero_gde("basura")

    def test_vacio(self):
        with pytest.raises(ValueError):
            partir_numero_gde("")


class TestEnriquecerGDE:
    def test_numero_valido(self, datos):
        _enriquecer_gde(datos, "IF-2024-123-APN-X", "", None, None)
        assert datos.gde_prefijo == "IF"
        assert datos.gde_numero == "2024-123"
        assert datos.gde_sufijo == "APN-X"
        assert datos.referencia_externa == "IF-2024-123-APN-X"

    def test_numero_cero(self, datos):
        _enriquecer_gde(datos, "IF-0", "", None, None)
        assert datos.referencia_externa == "IF-0"
        assert datos.gde_numero == "0"

    def test_crudo_none(self, datos):
        _enriquecer_gde(datos, None, "", None, None)
        assert datos.referencia_externa == ""
        assert datos.gde_numero is None

    def test_partir_falla_avisa(self, datos):
        _enriquecer_gde(datos, "basura", "", None, None)
        assert datos.referencia_externa == ""

    def test_encabezado_coincide_con_pdf(self, datos):
        _enriquecer_gde(datos, None, "",
                        "IF-2024-123-APN-X", "IF-2024-123-APN-X.pdf")
        assert not any("Confirme" in a for a in datos.avisos)

    def test_encabezado_difiere(self, datos):
        _enriquecer_gde(datos, None, "", "IF-2024-AAA", "IF-2024-BBB.pdf")
        assert any("Confirme" in a for a in datos.avisos)

    def test_mencionados_preserva_orden(self, datos):
        texto = "Ref IF-2024-1-APN-A y IF-2024-2-APN-B y IF-2024-1-APN-A"
        _enriquecer_gde(datos, None, texto, None, None)
        assert datos.mencionados == ["IF-2024-1-APN-A", "IF-2024-2-APN-B"]

    def test_crudo_excluido_de_mencionados(self, datos):
        texto = "El doc IF-2024-1-APN-A menciona IF-2024-2-APN-B"
        _enriquecer_gde(datos, "IF-2024-1-APN-A", texto, None, None)
        assert datos.mencionados == ["IF-2024-2-APN-B"]


class TestDetectores:
    def test_detectar_orden(self):
        assert detectar_orden("ORDEN DEL DIA: 123") == "123"
        assert detectar_orden("sin orden") is None

    def test_detectar_termino(self):
        r = detectar_termino("termino hasta 31/12/2026 para responder")
        assert r is not None
        assert r[0] == date(2026, 12, 31)

    def test_detectar_termino_invalido(self):
        assert detectar_termino("termino hasta 32/13/2026") is None

    def test_pide_difusion(self):
        assert pide_difusion("difundir a todas las areas") is True
        assert pide_difusion("nada relevante") is False


class TestExtraer:
    def test_texto_vacio_retorna_temprano(self, mocker, ruta):
        mocker.patch("parser.texto_de_archivo", return_value=("", ["aviso"]))
        r = extraer(ruta)
        assert r.avisos == ["aviso"]
        assert r.texto == ""

    def test_formato_desconocido(self, mocker, ruta):
        mocker.patch("parser.texto_de_archivo", return_value=("cuerpo cualquiera", []))
        mocker.patch("parser.analizar_correo_aeronautico", return_value=None)
        mocker.patch("parser.analizar_nota_gde", return_value=None)

        r = extraer(ruta)
        assert any("no se reconocio" in a for a in r.avisos)
        assert r.detalle == "cuerpo cualquiera"

    def test_orden_respeta_previo(self, mocker, ruta):
        mocker.patch("parser.texto_de_archivo", return_value=("cuerpo", []))
        previos = Extraccion(orden="ORDEN-PREVIO", adjunto_referencia="ref")
        mocker.patch("parser.analizar_correo_aeronautico", return_value=previos)
        mocker.patch("parser.analizar_nota_gde", return_value=None)

        r = extraer(ruta)
        assert r.orden == "ORDEN-PREVIO"

    def test_termino_detectado(self, mocker, ruta):
        mocker.patch("parser.texto_de_archivo",
                     return_value=("termino hasta 31/12/2026", []))
        mocker.patch("parser.analizar_correo_aeronautico", return_value=Extraccion())
        mocker.patch("parser.analizar_nota_gde", return_value=None)

        r = extraer(ruta)
        assert r.termino == date(2026, 12, 31)
        assert any("31/12/2026" in a for a in r.avisos)

    def test_difusion_sin_orden_avisa(self, mocker, ruta):
        mocker.patch("parser.texto_de_archivo",
                     return_value=("hay que difundir esto", []))
        mocker.patch("parser.analizar_correo_aeronautico", return_value=Extraccion())
        mocker.patch("parser.analizar_nota_gde", return_value=None)

        r = extraer(ruta)
        assert r.requiere_difusion is True
        assert any("falta la orden" in a for a in r.avisos)
