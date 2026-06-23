#%%
import os
import json
import smtplib
import pickle
import base64
import pandas as pd
import plotly.express as px
import streamlit as st
import yaml
import io

from datetime import datetime, time, timedelta
from pathlib import Path
from yaml.loader import SafeLoader
from PIL import Image

from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Border

import streamlit_authenticator as stauth

import numpy as np
import re
import unicodedata
import zipfile
from xml.etree import ElementTree as ET


ROTA_COLUMN_MAP = {
    'Grupo': 'nome grupo',
    'Horário': 'horario',
    'Unidade': 'unidade',
    'STATUS': 'status',
    'Dias da Semana': 'dias da semana',
    'STAGE': 'stage',
    'MODALIDADE': 'modalidade',
    'GRUPO': 'grupo',
    'N Aulas': 'n aulas',
    'PARAG ATUAL': 'parag atual grupo',
    'PARAG FINAL': 'parag_final_grupo',
    'TEACHERS': 'teacher',
    'Rescisão': 'rescisao',
    'Permuta': 'permuta',
    'Bolsista': 'bolsista',
    'N TOTAL ALUNOS': 'n_total_alunos',
}

ROTA_DISPLAY_MAP = {v: k for k, v in ROTA_COLUMN_MAP.items()}

ROTA_EXPORT_COLUMNS = [
    'Grupo', 'Horário', 'Unidade', 'STATUS', 'Dias da Semana', 'STAGE',
    'MODALIDADE', 'GRUPO', 'N Aulas', 'PARAG ATUAL', 'PARAG FINAL', 'TEACHERS',
    'N', 'Rescisão', 'Permuta', 'Bolsista', 'N TOTAL ALUNOS',
]

UNIDADE_DISPLAY = {
    'JARDIM': 'Jardim',
    'SATÉLITE': 'Satélite',
    'VICENTINA': 'Vicentina',
}


def _normalize_horario_value(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, time):
        return value.strftime('%H:%M:%S')
    if isinstance(value, datetime):
        return value.strftime('%H:%M:%S')
    if isinstance(value, pd.Timestamp):
        return value.strftime('%H:%M:%S')
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        parsed = pd.to_datetime(value, unit='D', origin='1899-12-30', errors='coerce')
        if pd.notna(parsed):
            return parsed.strftime('%H:%M:%S')

    text = str(value).strip()
    if not text or text.lower() in ('nan', 'none', '<na>'):
        return np.nan

    parsed = pd.to_datetime(text, errors='coerce')
    if pd.notna(parsed):
        return parsed.strftime('%H:%M:%S')
    return text


def _normalize_stage(value):
    if pd.isna(value):
        return value
    if isinstance(value, (int, np.integer)):
        return f'ESTAGIO_{value}'
    if isinstance(value, float) and not np.isnan(value) and value == int(value):
        return f'ESTAGIO_{int(value)}'
    text = str(value).strip()
    if text.isdigit():
        return f'ESTAGIO_{text}'
    return text


def _stringify_column_name(column) -> str:
    if hasattr(column, 'strftime'):
        return column.strftime('%H:%M:%S')
    return str(column).strip()


def _normalize_rota_values(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if 'unidade' in df.columns:
        df['unidade'] = df['unidade'].astype(str).str.strip().str.upper()

    if 'status' in df.columns:
        df['status'] = df['status'].astype(str).str.strip().str.upper()
        df['status'] = df['status'].replace({'NAN': np.nan, 'NONE': np.nan})

    if 'horario' in df.columns:
        df['horario'] = df['horario'].apply(_normalize_horario_value)

    if 'stage' in df.columns:
        df['stage'] = df['stage'].apply(_normalize_stage)

    if 'teacher' in df.columns:
        df['teacher'] = (
            df['teacher']
            .astype(str)
            .str.strip()
            .replace({'': '-', 'nan': '-', 'NaN': '-', 'None': '-', '<NA>': '-'})
        )

    if 'ultimo_professor' not in df.columns and 'teacher' in df.columns:
        df['ultimo_professor'] = df['teacher']

    if 'penultimo_professor' not in df.columns:
        df['penultimo_professor'] = '-'

    if 'restricoes_professor' not in df.columns:
        df['restricoes_professor'] = np.nan

    df = df.loc[~df['nome grupo'].isnull()].copy()
    df = df[df['nome grupo'].astype(str).str.strip() != ''].copy()

    return df


def _find_rota_sheet(wb) -> tuple[str, int, str | None]:
    if wb.active['A2'].value == 'Grupo':
        a1 = wb.active['A1'].value
        titulo = str(a1).strip() if a1 and 'ROTA' in str(a1).upper() else None
        return wb.active.title, 1, titulo

    for name in wb.sheetnames:
        ws = wb[name]
        if ws['A2'].value == 'Grupo':
            a1 = ws['A1'].value
            titulo = str(a1).strip() if a1 and 'ROTA' in str(a1).upper() else None
            return name, 1, titulo
        if ws['A1'].value == 'Grupo':
            return name, 0, None

    raise ValueError(
        'Nenhuma aba de rota encontrada. Esperado cabeçalho "Grupo" na linha 1 ou 2.'
    )


def load_rota_excel(file) -> tuple[pd.DataFrame, str | None, str]:
    """
    Lê o Excel da rota no formato do usuário (linha mesclada + cabeçalho)
    e normaliza colunas para o padrão interno do sistema.

    Retorna o DataFrame normalizado, o título da rota e o nome da aba utilizada.
    """
    wb = load_workbook(file, read_only=True, data_only=True)
    if hasattr(file, 'seek'):
        file.seek(0)

    sheet_name, skiprows, titulo = _find_rota_sheet(wb)
    wb.close()

    df = pd.read_excel(file, sheet_name=sheet_name, skiprows=skiprows)

    if 'nome grupo' not in df.columns:
        df = df.rename(columns=ROTA_COLUMN_MAP)

    return _normalize_rota_values(df), titulo, sheet_name


def parse_rota_titulo(titulo: str | None) -> tuple[str | None, str | None]:
    if not titulo:
        return None, None
    match = re.search(
        r'ROTA\s+(\d{2}/\d{2})\s+A\s+(\d{2}/\d{2})',
        str(titulo).strip(),
        re.IGNORECASE,
    )
    if match:
        return match.group(1), match.group(2)
    return None, None


def parse_dd_mm_to_date(dd_mm: str):
    day, month = dd_mm.split('/')
    return datetime(datetime.now().year, int(month), int(day)).date()


def build_rota_titulo(data_inicio: str, data_fim: str) -> str:
    inicio = data_inicio.strip()
    fim = data_fim.strip()
    if inicio and fim:
        return f"ROTA {inicio} A {fim}"
    if inicio:
        return f"ROTA {inicio}"
    return f"ROTA GERADA {datetime.now().strftime('%d/%m/%Y')}"


def format_rota_for_export(df: pd.DataFrame) -> pd.DataFrame:
    export_df = df.rename(columns=ROTA_DISPLAY_MAP)

    if 'Unidade' in export_df.columns:
        export_df['Unidade'] = export_df['Unidade'].map(
            lambda value: UNIDADE_DISPLAY.get(str(value).strip().upper(), value)
        )

    if 'TEACHERS' in export_df.columns:
        export_df['TEACHERS'] = export_df['TEACHERS'].replace('-', '')

    cols = [col for col in ROTA_EXPORT_COLUMNS if col in export_df.columns]
    extra_cols = [col for col in export_df.columns if col not in cols]
    return export_df[cols + extra_cols]


def _rota_header_row(worksheet) -> int:
    if worksheet.cell(row=2, column=1).value in ('Grupo', 'nome grupo'):
        return 2
    return 1


def _rota_data_start_row(worksheet) -> int:
    return _rota_header_row(worksheet) + 1


def _teacher_display_value(teacher) -> str | None:
    if teacher is None or pd.isna(teacher):
        return None
    value = str(teacher).strip()
    if value in ('', '-', 'nan', 'NaN', 'None', '<NA>'):
        return None
    return value


SHEET_MAIN_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
SHEET_NS = {'m': SHEET_MAIN_NS}
REL_ID_ATTR = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
ET.register_namespace('', SHEET_MAIN_NS)


def _resolve_workbook_sheet_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    wb = ET.fromstring(zf.read('xl/workbook.xml'))
    rels = ET.fromstring(zf.read('xl/_rels/workbook.xml.rels'))
    rid_map = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels}
    for sheet in wb.findall('.//m:sheets/m:sheet', SHEET_NS):
        if sheet.attrib.get('name') == sheet_name:
            target = rid_map[sheet.attrib[REL_ID_ATTR]]
            return 'xl/' + target.lstrip('/')
    raise ValueError(f'Aba "{sheet_name}" não encontrada no template.')


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if 'xl/sharedStrings.xml' not in zf.namelist():
        return []
    root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
    strings = []
    for item in root.findall('m:si', SHEET_NS):
        text = item.find('m:t', SHEET_NS)
        if text is not None:
            strings.append(text.text or '')
            continue
        parts = []
        for run in item.findall('m:r', SHEET_NS):
            run_text = run.find('m:t', SHEET_NS)
            if run_text is not None and run_text.text:
                parts.append(run_text.text)
        strings.append(''.join(parts))
    return strings


def _xml_escape(text: str) -> str:
    return (
        text.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def _replace_si_text_at_index(shared_xml: bytes, index: int, new_text: str) -> bytes:
    text = shared_xml.decode('utf-8')
    matches = list(re.finditer(r'<si>(?:.*?)</si>', text, flags=re.DOTALL))
    if index >= len(matches):
        return shared_xml
    match = matches[index]
    new_si = f'<si><t>{_xml_escape(new_text)}</t></si>'
    return (text[:match.start()] + new_si + text[match.end():]).encode('utf-8')


def _get_shared_string_index(cell) -> int | None:
    if cell is None or cell.attrib.get('t') != 's':
        return None
    value = cell.find('m:v', SHEET_NS)
    if value is None or value.text is None:
        return None
    return int(value.text)


def _normalize_grupo_key(value) -> str:
    return unicodedata.normalize('NFC', str(value).strip())


def _append_shared_string(shared_xml: bytes, new_text: str) -> tuple[bytes, int]:
    text = shared_xml.decode('utf-8')
    matches = list(re.finditer(r'<si>(?:.*?)</si>', text, flags=re.DOTALL))
    new_index = len(matches)
    new_si = f'<si><t>{_xml_escape(new_text)}</t></si>'
    text = text.replace('</sst>', new_si + '</sst>', 1)
    text = re.sub(
        r'uniqueCount="(\d+)"',
        lambda match: f'uniqueCount="{int(match.group(1)) + 1}"',
        text,
        count=1,
    )
    text = re.sub(
        r'count="(\d+)"',
        lambda match: f'count="{int(match.group(1)) + 1}"',
        text,
        count=1,
    )
    return text.encode('utf-8'), new_index


def _set_cell_shared_index(sheet_xml: bytes, cell_ref: str, index: int) -> bytes:
    text = sheet_xml.decode('utf-8')
    pattern = rf'<c r="{re.escape(cell_ref)}"([^>/]*)(?:/>|>(?:.*?</c>))'

    def replacer(match):
        attrs = match.group(1)
        attrs = re.sub(r'\s*t="[^"]*"', '', attrs)
        return f'<c r="{cell_ref}"{attrs} t="s"><v>{index}</v></c>'

    new_text, replacements = re.subn(pattern, replacer, text, count=1, flags=re.DOTALL)
    if replacements:
        return new_text.encode('utf-8')

    row_number = int(''.join(ch for ch in cell_ref if ch.isdigit()))
    col_letter = ''.join(ch for ch in cell_ref if ch.isalpha())
    row_pattern = rf'(<row r="{row_number}"[^>]*>)(.*?)(</row>)'
    row_match = re.search(row_pattern, text, flags=re.DOTALL)
    if row_match is None:
        return sheet_xml

    new_cell = f'<c r="{cell_ref}" t="s"><v>{index}</v></c>'
    updated_row = row_match.group(1) + row_match.group(2) + new_cell + row_match.group(3)
    return (text[:row_match.start()] + updated_row + text[row_match.end():]).encode('utf-8')


def _build_rota_patch_targets(
    sheet_xml: bytes,
    strings: list[str],
) -> tuple[int | None, dict[str, str]]:
    root = ET.fromstring(sheet_xml)
    header_row = 2 if _find_row(root, 2) is not None else 1
    data_start = header_row + 1
    grupo_col = _find_header_column(root, strings, 'Grupo', header_row) or 'A'
    teachers_col = _find_header_column(root, strings, 'TEACHERS', header_row) or 'L'

    title_row = _find_row(root, 1)
    title_ss_index = _get_shared_string_index(_find_cell(title_row, 'A1')) if title_row is not None else None

    teacher_cells = {}
    for row in root.findall('.//m:sheetData/m:row', SHEET_NS):
        row_number = int(row.attrib.get('r', 0))
        if row_number < data_start:
            continue
        grupo = _resolve_cell_text(_find_cell(row, f'{grupo_col}{row_number}'), strings)
        if not grupo:
            continue
        teacher_cells[_normalize_grupo_key(grupo)] = f'{teachers_col}{row_number}'

    return title_ss_index, teacher_cells


def _patch_rota_workbook(
    shared_xml: bytes,
    sheet_xml: bytes,
    titulo: str,
    teachers_by_grupo: dict[str, str | None],
    title_ss_index: int | None,
    teacher_cells: dict[str, str],
) -> tuple[bytes, bytes]:
    patched_shared = shared_xml
    patched_sheet = sheet_xml
    teacher_string_cache: dict[str, int] = {}

    if title_ss_index is not None:
        patched_shared = _replace_si_text_at_index(patched_shared, title_ss_index, titulo)

    for grupo, teacher in teachers_by_grupo.items():
        if not teacher:
            continue
        cell_ref = teacher_cells.get(_normalize_grupo_key(grupo))
        if not cell_ref:
            continue

        if teacher not in teacher_string_cache:
            patched_shared, teacher_string_cache[teacher] = _append_shared_string(patched_shared, teacher)

        patched_sheet = _set_cell_shared_index(
            patched_sheet,
            cell_ref,
            teacher_string_cache[teacher],
        )

    return patched_shared, patched_sheet


def _cell_ref_parts(ref: str) -> tuple[str, int]:
    col = ''.join(ch for ch in ref if ch.isalpha())
    row = int(''.join(ch for ch in ref if ch.isdigit()))
    return col, row


def _find_row(sheet_root, row_number: int):
    for row in sheet_root.findall('.//m:sheetData/m:row', SHEET_NS):
        if int(row.attrib.get('r', 0)) == row_number:
            return row
    return None


def _find_cell(row, ref: str):
    for cell in row.findall('m:c', SHEET_NS):
        if cell.attrib.get('r') == ref:
            return cell
    return None


def _resolve_cell_text(cell, strings: list[str]) -> str | None:
    if cell is None:
        return None
    cell_type = cell.attrib.get('t')
    value = cell.find('m:v', SHEET_NS)
    if cell_type == 's' and value is not None and value.text is not None:
        return strings[int(value.text)]
    if cell_type == 'inlineStr':
        inline = cell.find('m:is/m:t', SHEET_NS)
        return inline.text if inline is not None else None
    if value is not None:
        return value.text
    return None


def _find_header_column(sheet_root, strings: list[str], header_name: str, header_row: int = 2) -> str | None:
    row = _find_row(sheet_root, header_row)
    if row is None:
        return None
    for cell in row.findall('m:c', SHEET_NS):
        if _resolve_cell_text(cell, strings) == header_name:
            return _cell_ref_parts(cell.attrib['r'])[0]
    return None


def _clone_zip_with_patches(template_bytes: bytes, patches: dict[str, bytes]) -> bytes:
    in_zip = zipfile.ZipFile(io.BytesIO(template_bytes), 'r')
    out_buf = io.BytesIO()
    with zipfile.ZipFile(out_buf, 'w') as out_zip:
        for item in in_zip.infolist():
            data = patches.get(item.filename, in_zip.read(item.filename))
            out_zip.writestr(item, data, compress_type=item.compress_type)
    in_zip.close()
    return out_buf.getvalue()


def _export_rota_from_template(
    df: pd.DataFrame,
    titulo: str,
    template_bytes: bytes,
    sheet_name: str | None = None,
) -> bytes:
    teachers_by_grupo = {}
    for _, row in df.iterrows():
        if pd.isna(row.get('nome grupo')):
            continue
        grupo = _normalize_grupo_key(row['nome grupo'])
        teacher = _teacher_display_value(row.get('teacher'))
        if teacher:
            teachers_by_grupo[grupo] = teacher

    with zipfile.ZipFile(io.BytesIO(template_bytes), 'r') as zf:
        if sheet_name is None:
            wb = ET.fromstring(zf.read('xl/workbook.xml'))
            active_id = wb.find('.//m:bookViews/m:workbookView', SHEET_NS).attrib.get('activeTab', '0')
            sheets = wb.findall('.//m:sheets/m:sheet', SHEET_NS)
            sheet_name = sheets[int(active_id)].attrib['name']
        sheet_path = _resolve_workbook_sheet_path(zf, sheet_name)
        strings = _read_shared_strings(zf)
        sheet_xml = zf.read(sheet_path)
        shared_xml = zf.read('xl/sharedStrings.xml')

    title_ss_index, teacher_cells = _build_rota_patch_targets(sheet_xml, strings)
    patched_shared, patched_sheet = _patch_rota_workbook(
        shared_xml,
        sheet_xml,
        titulo,
        teachers_by_grupo,
        title_ss_index,
        teacher_cells,
    )
    return _clone_zip_with_patches(template_bytes, {
        'xl/sharedStrings.xml': patched_shared,
        sheet_path: patched_sheet,
    })


def _export_rota_plain(df: pd.DataFrame, titulo: str) -> bytes:
    export_df = format_rota_for_export(df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame([[titulo]]).to_excel(
            writer, index=False, header=False, startrow=0, sheet_name='Rotas'
        )
        export_df.to_excel(writer, index=False, sheet_name='Rotas', startrow=1)
        ws = writer.sheets['Rotas']
        ws.merge_cells(
            start_row=1, start_column=1, end_row=1, end_column=max(len(export_df.columns), 1)
        )

        header_fill = PatternFill(patternType='solid', fgColor='FF000000')
        header_font = Font(color='FFFFFFFF', bold=True)
        title_font = Font(color='FFFFFFFF', bold=True)
        data_fill = PatternFill(patternType='solid', fgColor='FFFFFFFF')
        green_header_fill = PatternFill(patternType='solid', fgColor='FF8BC34A')
        green_header_font = Font(color='FF000000', bold=True)

        for col in range(1, len(export_df.columns) + 1):
            cell = ws.cell(row=2, column=col)
            if col == len(export_df.columns) and export_df.columns[-1] == 'N TOTAL ALUNOS':
                cell.fill = green_header_fill
                cell.font = green_header_font
            else:
                cell.fill = header_fill
                cell.font = header_font

        ws['A1'].fill = header_fill
        ws['A1'].font = title_font

        for row_idx in range(3, 3 + len(export_df)):
            for col in range(1, len(export_df.columns) + 1):
                ws.cell(row=row_idx, column=col).fill = data_fill

    return output.getvalue()


def export_rota_excel(
    df: pd.DataFrame,
    titulo: str | None = None,
    template_bytes: bytes | None = None,
    sheet_name: str | None = None,
) -> bytes:
    if not titulo:
        titulo = f"ROTA GERADA {datetime.now().strftime('%d/%m/%Y')}"

    if template_bytes:
        return _export_rota_from_template(df, titulo, template_bytes, sheet_name)
    return _export_rota_plain(df, titulo)


def _set_row_hidden_flag(sheet_text: str, row_num: int, hidden: bool) -> str:
    pattern = rf'(<row r="{row_num}"[^>]*?)>'
    match = re.search(pattern, sheet_text)
    if not match:
        return sheet_text
    row_tag = re.sub(r'\s*hidden="1"', '', match.group(1))
    if hidden:
        row_tag += ' hidden="1"'
    return sheet_text[:match.start()] + row_tag + '>' + sheet_text[match.end():]


def _filter_rota_sheet_for_groups(
    sheet_xml: bytes,
    strings: list[str],
    allowed_grupos: set[str],
) -> bytes:
    _, teacher_cells = _build_rota_patch_targets(sheet_xml, strings)
    allowed = {_normalize_grupo_key(grupo) for grupo in allowed_grupos}
    visible_rows = {1, 2}

    for grupo, cell_ref in teacher_cells.items():
        if grupo in allowed:
            visible_rows.add(int(''.join(ch for ch in cell_ref if ch.isdigit())))

    sheet_text = sheet_xml.decode('utf-8')
    for row_match in re.finditer(r'<row r="(\d+)"', sheet_text):
        row_num = int(row_match.group(1))
        sheet_text = _set_row_hidden_flag(sheet_text, row_num, row_num not in visible_rows)

    return sheet_text.encode('utf-8')


def _export_rota_for_teacher(
    template_bytes: bytes,
    allowed_grupos: list[str],
    sheet_name: str | None = None,
) -> bytes:
    with zipfile.ZipFile(io.BytesIO(template_bytes), 'r') as zf:
        if sheet_name is None:
            wb = ET.fromstring(zf.read('xl/workbook.xml'))
            active_id = wb.find('.//m:bookViews/m:workbookView', SHEET_NS).attrib.get('activeTab', '0')
            sheets = wb.findall('.//m:sheets/m:sheet', SHEET_NS)
            sheet_name = sheets[int(active_id)].attrib['name']
        sheet_path = _resolve_workbook_sheet_path(zf, sheet_name)
        strings = _read_shared_strings(zf)
        sheet_xml = zf.read(sheet_path)

    filtered_sheet = _filter_rota_sheet_for_groups(sheet_xml, strings, allowed_grupos)
    return _clone_zip_with_patches(template_bytes, {sheet_path: filtered_sheet})


def replicate_row(row: pd.Series, times: int) -> pd.DataFrame:
    hora_inicial = pd.to_datetime(row['horario'], format='%H:%M:%S')
    novas_linhas = []
    for i in range(times):
        nova_linha = row.copy()
        nova_linha['horario'] = (hora_inicial + pd.Timedelta(hours=i)).strftime('%H:%M:%S')
        novas_linhas.append(nova_linha)
    return pd.DataFrame(novas_linhas)

def desaninhar_dias(df):
    df['dias da semana'] = df['dias da semana'].str.split(',')
    df = df.explode('dias da semana')
    return df

def expand_rows( df: pd.DataFrame, func) -> pd.DataFrame:
    return pd.concat(df.apply(func, axis=1).tolist(), ignore_index=True)

def clean_data(df: pd.DataFrame)-> pd.DataFrame:

    df['intenviso'] = np.where(df['n aulas']>=10,1,0)

    df['dias da semana'] = df['dias da semana'].str.replace('●',',').str.replace(' ','').str.replace('-','').str.replace('DOUBLE',',').str.replace('SINGLE','').str.replace('TRIPLE','').str.split(',')
    df = df.explode('dias da semana').reset_index(drop=True)

    df['dias da semana'] = df['dias da semana'].str.replace('ª','ª,').str.split(',')
    df = df.explode('dias da semana').reset_index(drop=True)

    df = df[df['dias da semana']!=''].copy()

    substituicoes = {
        '2ª': 'SEGUNDA',
        '3ª': 'TERÇA',
        '4ª': 'QUARTA',
        '5ª': 'QUINTA',
        '6ª': 'SEXTA',
        'SATURDAY': 'SÁBADO'
    }

    df['dias da semana'] = df['dias da semana'].replace(substituicoes, regex=True)

    df['status'] = df['status'].fillna('PRESENCIAL')

    df['horario_tratado'] = pd.to_datetime(df['horario'], format='%H:%M:%S')

    return df

def filter_class_without_teacher(df: pd.DataFrame) -> pd.DataFrame:
    return df[((df['teacher'].isnull()) | (df['teacher']=='-'))]

def base_selection(df: pd.DataFrame) -> tuple:
    aulas_tratadas = df.loc[~df['nome grupo'].isnull()]

    aulas = aulas_tratadas.copy()
    # tratando os dados para colocar cada linha uma aula
    aulas['dias da semana'] = aulas['dias da semana'].str.upper()
    aulas['dias da semana'] = aulas['dias da semana'].str.replace('EVERYDAY','2ª ● 3ª ● 4ª ● 5ª ● 6ª')
    aulas['stage'] = aulas['stage'].apply(_normalize_stage)
    aulas['ultimo_professor'] = aulas['ultimo_professor'].astype(str)
    aulas['penultimo_professor'] = aulas['penultimo_professor'].astype(str)


    # separando as aulas que são triplas, duplas e o resto
    tri = aulas.loc[aulas['dias da semana'].str.contains('TRIPLE')]
    doub = aulas.loc[aulas['dias da semana'].str.contains('DOUBLE')]
    aulas_simples = aulas[~aulas['dias da semana'].str.contains('DOUBLE|TRIPLE')].copy()

    # tratando a colunas horario
    aulas_simples['horario'] = pd.to_datetime(aulas_simples['horario'],format='%H:%M:%S').dt.strftime('%H:%M:%S')
    return aulas_simples, doub, tri

def transform_classes_dateframe(aulas_raw):
    #aulas_filtrada = filter_class_without_teacher(aulas_raw)
    aulas_simples,doub,tri=base_selection(aulas_raw)

    # transformando aulas duplas/triplas em 2/3 linhas
    try:
        aulas_duplicadas = expand_rows(doub, lambda row: replicate_row(row, times=2))
    except Exception as e:
        aulas_duplicadas = pd.DataFrame(columns=aulas_simples.columns)
    try:    
        aulas_triplicadas = expand_rows(tri, lambda row: replicate_row(row, times=3))
    except Exception as e:
        aulas_triplicadas = pd.DataFrame(columns=aulas_simples.columns)
    # juntando todas as linhas
    df_tratado = pd.concat([aulas_simples, aulas_duplicadas, aulas_triplicadas], ignore_index=True)

    df_result = clean_data(df_tratado)

    return df_result

def transform_teacher_dataframe(professores_raw):
    professores_raw = professores_raw.copy()
    professores_raw.columns = [_stringify_column_name(col) for col in professores_raw.columns]
    if professores_raw.columns.str.contains('FERIAS').any():
        professores_raw = professores_raw[professores_raw['FERIAS']!=1].copy()
    return professores_raw

def transform_alocation_dataframe(aulas_raw,base_alocada):
    alocation_df = pd.merge(aulas_raw, base_alocada, on='nome grupo', how='left')
    alocation_df['penultimo_professor'] = alocation_df['ultimo_professor']
    alocation_df.loc[alocation_df['professores_alocados'].notnull(), 'teacher'] = alocation_df.loc[alocation_df['professores_alocados'].notnull(), 'professores_alocados']
    alocation_df['ultimo_professor'] = alocation_df['teacher']
    alocation_df.drop(columns=['professores_alocados'], inplace=True)
    not_alocation_df = alocation_df.loc[((alocation_df['teacher'].isnull())|(alocation_df['teacher']=='-'))].copy()
    return alocation_df, not_alocation_df

def enviar_email_para_todos(combined_df, arquivo_rota):
    log_messages = []
    failed_teachers = []

    if hasattr(arquivo_rota, 'getvalue'):
        template_bytes = arquivo_rota.getvalue()
    elif isinstance(arquivo_rota, (bytes, bytearray)):
        template_bytes = bytes(arquivo_rota)
    else:
        with open(arquivo_rota, 'rb') as file:
            template_bytes = file.read()

    _, _, sheet_name = load_rota_excel(io.BytesIO(template_bytes))

    with open('.devcontainer/config.json') as f:
        config = json.load(f)

    from_email = 'teacher.scheduler.contact@gmail.com'
    password = config["email_password"]

    for teacher in combined_df['Teacher'].unique():
        professor_data = combined_df[combined_df['Teacher'] == teacher]

        if professor_data.empty or pd.isna(teacher) or str(teacher).strip() == '':
            continue

        if 'Email' not in professor_data.columns or pd.isna(professor_data['Email'].values[0]):
            log_messages.append(f"❌ No email found for {teacher}")
            failed_teachers.append(teacher)
            continue

        nome_grupo = professor_data['Nome Grupo'].dropna().astype(str).tolist()
        email_professor = professor_data['Email'].values[0]
        filtered_xlsx = _export_rota_for_teacher(template_bytes, nome_grupo, sheet_name)

        nome_grupo_formatado = "\n".join(f"    {grupo}" for grupo in nome_grupo)
        message = (
            f"Hello {teacher},\n\n"
            f"You have been assigned to the following classes:\n\n"
            f"{nome_grupo_formatado}\n\n"
            f"Please find attached your detailed class schedule.\n\n"
            f"Best regards,\n"
            f"The Family Idiomas"
        )

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = email_professor
        msg['Subject'] = 'Your Class Schedule'
        msg.attach(MIMEText(message, 'plain'))

        safe_name = re.sub(r'[<>:"/\\|?*]+', '_', str(teacher).strip())
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(filtered_xlsx)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{safe_name}_schedule.xlsx"',
        )
        msg.attach(part)

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, email_professor, msg.as_string())
            server.quit()
            log_messages.append(f"✅ Email sent successfully to {teacher}")
        except Exception:
            log_messages.append(f"❌ Failed to send email to {teacher}")
            failed_teachers.append(teacher)

    st.session_state.failed_teachers = failed_teachers
    return log_messages