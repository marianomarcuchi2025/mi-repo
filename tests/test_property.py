"""Property-based tests con Hypothesis."""
import re
from hypothesis import given, example, settings, HealthCheck
from hypothesis import strategies as st
from parser import Extraccion, _enriquecer_gde, _norm


class TestNormProperties:
    @given(st.text())
    def test_solo_alfanumericos_mayusculas(self, s):
        assert re.fullmatch(r"[A-Z0-9]*", _norm(s))

    @given(st.text())
    def test_idempotente(self, s):
        assert _norm(_norm(s)) == _norm(s)

    @given(st.text())
    def test_case_insensitive(self, s):
        assert _norm(s.upper()) == _norm(s.lower())

    @example("")
    @example("IF-2024-123.pdf")
    @given(st.text())
    def test_invariante(self, s):
        r = _norm(s)
        assert r == r.upper()
        assert all(c.isalnum() for c in r)


class TestEnriquecerProperties:
    @given(st.text(max_size=200), st.text(max_size=100),
           st.one_of(st.none(), st.text(max_size=50)),
           st.one_of(st.none(), st.text(max_size=50)))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_fuzz_no_explota(self, texto, crudo, encabezado, nombre):
        datos = Extraccion()
        _enriquecer_gde(datos, crudo, texto, encabezado, nombre)
        assert isinstance(datos.avisos, list)
        assert isinstance(datos.mencionados, list)

    @given(st.text(min_size=1))
    def test_encabezado_igual_nombre_no_avisa(self, s):
        datos = Extraccion()
        _enriquecer_gde(datos, None, "", s, s)
        assert not any("Confirme" in a for a in datos.avisos)
