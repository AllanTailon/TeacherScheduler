# TeacherScheduler

Streamlit app for **The Family Idiomas** that assigns teachers to class groups using Google OR-Tools CP-SAT, with Excel I/O and optional e-mail distribution.

## Features

- Upload weekly **rota** and **teacher capability** Excel files
- Validate pre-allocations before solving
- Allocate remaining groups with a soft-constraint ladder (levels 0 → 1 → 2)
- Export allocated rota (preserves original Excel template when possible)
- E-mail each teacher a filtered copy of their schedule

## Quick start

```bash
cd streamlit_app
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp ../.env.example ../.env   # then edit secrets
streamlit run Pagina_principal_app.py
```

From the repo root:

```bash
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/Pagina_principal_app.py
```

## Secrets (required for e-mail / production auth)

Copy `.env.example` to `.env` (never commit `.env`):

| Variable | Purpose |
|----------|---------|
| `EMAIL_ADDRESS` | Gmail sender address |
| `EMAIL_PASSWORD` | Gmail **app password** (rotate if it was ever committed) |

> **Security:** Any Gmail app password previously stored in `.devcontainer/config.json` must be revoked in Google Account settings and replaced.

## Excel schemas

### Rota workbook

- Title row (optional): `ROTA dd/mm A dd/mm`
- Header row with at least: `Grupo`, `Horário`, `Unidade`, `STATUS`, `Dias da Semana`, `STAGE`, `MODALIDADE`, `GRUPO`, `N Aulas`, `TEACHERS`
- Days may use tokens like `2ª ● 4ª`, `EVERYDAY`, `DOUBLE`, `TRIPLE`
- Empty / `-` in `TEACHERS` means the group still needs allocation

### Teachers workbook

Required identity / capacity columns:

- `TEACHER`, `MEDIA`, `FERIAS`
- Unit flags: `SATÉLITE`, `JARDIM`, `VICENTINA`
- Mode flags: `ONLINE`, `PRESENCIAL`, `INTENSIVÃO`
- Group types: `Grupo`, `VIP`, `In Company`, `VIP - In Company`
- Modalities as needed (`Espanhol`, `Kids`, `MBA`, CONV-*, …)
- Stage columns `ESTAGIO_*`
- Day columns: `SEGUNDA` … `SÁBADO`
- Hour columns matching rota times (`HH:MM:SS`)
- Optional `Email` column for the send-rota page

## Soft constraint levels

| Level | Workload | Last-teacher preference |
|-------|----------|-------------------------|
| 0 | Hard band `[MEDIA-4, MEDIA]` | Soft avoid `ultimo` (strong) + `penultimo` (weak) |
| 1 | Soft target MEDIA (may exceed by up to `MEDIA_SOFT_OVERFLOW`) | Hard forbid `ultimo`; soft avoid `penultimo` |
| 2 | Soft target MEDIA with overflow + stronger over-MEDIA penalty | Soft avoid `ultimo` + `penultimo` |

Only levels **0, 1, 2** exist. The UI tries them in order until CP-SAT returns a feasible solution.

### Saturday rule

For classes on **SÁBADO**, teacher **hour** flags and **unidade** flags are ignored.
Anyone with `SÁBADO=1` in the teachers sheet may take those classes (other constraints such as modality, modality/group type, ONLINE/PRESENCIAL, and same-slot clashes still apply).

### Teacher history (`ultimo` / `penultimo`)

- After each allocation: `penultimo_professor` ← previous `ultimo_professor`, then `ultimo_professor` ← newly assigned teacher.
- On the next run the solver reads those columns (soft/hard avoid depending on constraint level).
- Blank / `-` / `nan` are treated as “no history”.
- History headers live on the title row of the rota Excel; export writes them back into the template.

## Project layout

```
streamlit_app/
  Pagina_principal_app.py   # UI
  teacher_allocation.py     # CP-SAT solver
  validator.py              # Pre-solve checks
  rota_io.py / transforms.py / export_ooxml.py / email_sender.py
  constants.py / config.py
  tests/
alocacao/                   # Offline diagnostic notebooks
```

## Tests

```bash
pip install -r streamlit_app/requirements.txt
pytest streamlit_app/tests -q
```

## Docker

```bash
cd streamlit_app
# export EMAIL_PASSWORD in the shell first
docker compose up --build
```

```bash
streamlit run streamlit_app/Pagina_principal_app.py
```
