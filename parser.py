"""Parser de documentos GDE y correo aeronáutico."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


PATRON_GDE = re.compile(r"\b[A-Z]{2,4}-\d{4}-\d+-[A-Z]+-\d+\b")


@dataclass
class Extraccion:
    gde_prefijo: str | None = None
    gde_numero: str | None = None
    gde_sufijo: str | None = None
    referencia_externa: str = ""
    asunto: str = ""
    adjunto_referencia: str = ""
    texto: str = ""
    detalle: str = ""
    orden: str | None = None
    termino: date | None = None
    termino_texto: str | None = None
    requiere_difusion: bool = False
    mencionados: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _add_aviso(datos: Extraccion, mensaje: str) -> None:
    if mensaje not in datos.avisos:
        datos.avisos.append(mensaje)


def _primer_match(detector, *fuentes):
    for fuente in fuentes:
        if fuente:
            resultado = detector(fuente)
            if resultado:
                return resultado
    return None


def partir_numero_gde(crudo: str) -> tuple[str, str, str]:
    if not crudo:
        raise ValueError("Numero vacio")
    partes = crudo.split("-", 2)
    if len(partes) < 2:
        raise ValueError(f"Formato invalido: {crudo}")
    prefijo = partes[0]
    numero = partes[1]
    sufijo = partes[2] if len(partes) > 2 else ""
    return prefijo, numero, sufijo


def _enriquecer_gde(datos, crudo, texto, del_encabezado, del_nombre):
    if crudo:
        try:
            datos.gde_prefijo, datos.gde_numero, datos.gde_sufijo = partir_numero_gde(crudo)
        except (TypeError, ValueError) as e:
            _add_aviso(datos, f"No se pudo interpretar el numero GDE '{crudo}': {e}")

    if crudo and datos.gde_numero not in (None, ""):
        datos.referencia_externa = crudo

    if del_encabezado and del_nombre and _norm(del_encabezado) != _norm(del_nombre):
        _add_aviso(datos,
            f"El documento dice {del_encabezado} pero el archivo se llama "
            f"{del_nombre}. Confirme cual corresponde.")

    texto_up = texto.upper()
    crudo_up = crudo.upper() if crudo else ""
    mencionados = list(dict.fromkeys(
        m.group(0) for m in PATRON_GDE.finditer(texto_up)
        if m.group(0) != crudo_up
    ))
    if mencionados:
        datos.mencionados = mencionados
        _add_aviso(datos,
            f"El documento menciona {len(mencionados)} numero(s) GDE "
            f"adicional(es) como antecedente.")


def detectar_orden(texto: str) -> str | None:
    m = re.search(r"ORDEN\s+DEL?\s+D[IÍ]A\s*[:\-]?\s*([A-Z0-9\-]+)",
                  texto, re.IGNORECASE)
    return m.group(1) if m else None


def detectar_termino(texto: str):
    m = re.search(r"t[eé]rmino\s+hasta\s+(\d{1,2})/(\d{1,2})/(\d{4})",
                  texto, re.IGNORECASE)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d), m.group(0)
        except ValueError:
            return None
    return None


def pide_difusion(texto: str) -> bool:
    return bool(re.search(r"difundir|difusi[oó]n", texto, re.IGNORECASE))


def texto_de_archivo(ruta):
    return "", []


def analizar_correo_aeronautico(texto):
    return None


def analizar_nota_gde(texto, ruta):
    return None


def extraer(ruta):
    texto, avisos = texto_de_archivo(ruta)
    if not texto:
        return Extraccion(avisos=list(avisos))

    datos = analizar_correo_aeronautico(texto) or analizar_nota_gde(texto, ruta)

    if datos is None:
        datos = Extraccion()
        datos.detalle = texto[:4000]
        avisos = avisos + [
            "Se leyo el texto del documento, pero no se reconocio el formato."
        ]

    datos.avisos = list(avisos) + list(datos.avisos or [])
    datos.texto = texto

    if not datos.orden:
        datos.orden = _primer_match(
            detectar_orden,
            datos.adjunto_referencia,
            datos.asunto,
            texto[:2500],
        )

    resultado = detectar_termino(texto)
    if resultado:
        datos.termino, datos.termino_texto = resultado
        _add_aviso(datos, f"El documento fija un termino: {datos.termino:%d/%m/%Y}.")

    datos.requiere_difusion = bool(pide_difusion(texto))
    if datos.requiere_difusion and not datos.orden:
        _add_aviso(datos, "El documento indica difundir: falta la orden del dia.")

    return datos
