"""Compatibility facade — prefer importing from rota_io, transforms, export_ooxml, email_sender."""

from export_ooxml import export_rota_excel, export_rota_for_teacher
from email_sender import enviar_email_para_todos
from rota_io import (
    ROTA_COLUMN_MAP,
    ROTA_DISPLAY_MAP,
    ROTA_EXPORT_COLUMNS,
    build_rota_titulo,
    format_rota_for_export,
    load_rota_excel,
    parse_dd_mm_to_date,
    parse_rota_titulo,
)
from transforms import (
    base_selection,
    clean_data,
    expand_rows,
    replicate_row,
    transform_allocation_dataframe,
    transform_alocation_dataframe,
    transform_classes_dataframe,
    transform_classes_dateframe,
    transform_teacher_dataframe,
)

__all__ = [
    "ROTA_COLUMN_MAP",
    "ROTA_DISPLAY_MAP",
    "ROTA_EXPORT_COLUMNS",
    "base_selection",
    "build_rota_titulo",
    "clean_data",
    "enviar_email_para_todos",
    "expand_rows",
    "export_rota_excel",
    "export_rota_for_teacher",
    "format_rota_for_export",
    "load_rota_excel",
    "parse_dd_mm_to_date",
    "parse_rota_titulo",
    "replicate_row",
    "transform_allocation_dataframe",
    "transform_alocation_dataframe",
    "transform_classes_dataframe",
    "transform_classes_dateframe",
    "transform_teacher_dataframe",
]
