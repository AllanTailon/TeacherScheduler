"""Named business-rule and runtime constants for TeacherScheduler."""

# Scheduling gaps / turnos
MIN_GAP_MINUTES = 50
MIDDAY_HOUR = 12
INTENSIVE_LESSON_THRESHOLD = 10

# Workload around teacher MEDIA
MEDIA_HARD_BAND = 4
MEDIA_DEVIATION_DIVISOR = 8
MEDIA_SOFT_OVERFLOW = 8  # soft levels 1/2 may exceed MEDIA by up to this many lessons
WEIGHT_MEDIA = 5
WEIGHT_MEDIA_OVER = 10  # prefer under-MEDIA over over-MEDIA when both are soft
WEIGHT_REPETICAO = 2  # legacy alias for ultimo soft weight
WEIGHT_ULTIMO = 3
WEIGHT_PENULTIMO = 1

SATURDAY = "SÁBADO"

# CP-SAT
SOLVER_TIME_LIMIT_SECONDS = 60

# Soft constraint ladder used by the UI (0 = strict … 2 = loose)
SOFT_LEVELS = (0, 1, 2)

# Domain lists
UNIDADE_LIST = ["SATÉLITE", "JARDIM", "VICENTINA"]
DAYS_OF_WEEK = ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO"]
MODALITY_LIST = [
    "Espanhol",
    "Kids",
    "CONV - Ing Básico",
    "CONV - Ing Prep",
    "CONV - Ing Intermed",
    "CONV - Ing Avançado",
    "CONV - Esp Prep",
    "CONV - Esp Intermed",
    "CONV - Esp Avançado",
    "MBA",
]
GROUP_TYPE_LIST = ["Grupo", "VIP", "In Company", "VIP - In Company"]

DAY_SUBSTITUTIONS = {
    "2ª": "SEGUNDA",
    "3ª": "TERÇA",
    "4ª": "QUARTA",
    "5ª": "QUINTA",
    "6ª": "SEXTA",
    "SATURDAY": "SÁBADO",
}

UNIDADE_DISPLAY = {
    "JARDIM": "Jardim",
    "SATÉLITE": "Satélite",
    "VICENTINA": "Vicentina",
}
