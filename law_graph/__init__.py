# SPDX-FileCopyrightText: 2026 visualcomments ip-law-course contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Адаптированный пайплайн «закон-граф»: подготовка датасета и модели
предиктивного анализа норм российского права.

Адаптация подхода top-papers-graph (причинно-следственные связи между научными
открытиями -> темпоральный граф знаний -> прогноз новых связей) на область
российского права: вместо связей между открытиями строятся связи вида
«внесение поправки -> изменение нормы права», а цель модели — предиктивный
анализ норм права (какие нормы вероятно будут изменены).
"""

from .schemas import (  # noqa: F401
    AmendmentType,
    LegalNorm,
    AmendmentEvent,
    LegalTriplet,
    LegalTaskInstance,
    norm_id,
)
from .graph_builder import (
    LegalKnowledgeGraph,
    build_event_stream,
    chronological_split,
    build_task_instances,
)
from .link_prediction import LegalLinkPredConfig, legal_link_prediction  # noqa: F401

__version__ = "0.1.0"
