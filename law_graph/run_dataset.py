#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI конвейера «закон-граф»: подготовка датасета и модели предиктивного
анализа норм российского права.

Адаптация top-papers-graph на область права:
- признаки заменены с научных публикаций на нормы права и поправки;
- причинно-следственные связи открытий заменены на связи «поправка ->
  изменение нормы»;
- модель учится предсказывать, какие нормы вероятно будут изменены.

Примеры (запуск из корня репозитория):
  # офлайн-демо на синтетическом корпусе поправок (без внешних данных)
  python -m law_graph.run_dataset --mode synthetic --out runs/law_demo

  # реальный корпус из COURSE_CORPUS_ROOT/txt
  python -m law_graph.run_dataset --mode corpus --corpus-root "$COURSE_CORPUS_ROOT" --out runs/law_corpus
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from law_graph.corpus_loader import (
    load_synthetic_corpus,
    load_law_file,
    list_corpus_files,
    normalize_law,
)
from law_graph.amendment_extractor import (
    amendments_from_structured,
    influence_from_structured,
    rule_based_amendments_from_text,
)
from law_graph.schemas import AmendmentEvent, dump_jsonl
from law_graph.graph_builder import (
    LegalKnowledgeGraph,
    build_event_stream,
    chronological_split,
    build_task_instances,
    to_graph_snapshot,
)
from law_graph.link_prediction import LegalLinkPredConfig, LegalChangeHeuristic
from law_graph.model import fit_model, evaluate_predictions


def build_graph_from_synthetic() -> LegalKnowledgeGraph:
    syn = load_synthetic_corpus()
    events = amendments_from_structured(syn["amendments"]) + influence_from_structured(syn["influence"])
    kg = LegalKnowledgeGraph()
    for e in events:
        kg.add_event(e)
    kg.add_norms_from_events()
    return kg


def build_graph_from_corpus(root: str) -> LegalKnowledgeGraph:
    kg = LegalKnowledgeGraph()
    files = list_corpus_files(root)
    if not files:
        print(f"[corpus] в {root} нет txt/*.txt файлов; используйте --mode synthetic")
        return kg
    # Юридические файлы (законы, судебная практика) — best-effort правило-извлечение.
    for path in files:
        base = os.path.basename(path)
        law = normalize_law(base)
        try:
            chunks = load_law_file(path, source_law=law)
        except Exception:
            continue
        for chunk in chunks:
            text = chunk.text
            evs = rule_based_amendments_from_text(
                text,
                source_doc=chunk.source_doc,
                source_law=chunk.source_law,
                default_year=2020,
            )
            for e in evs:
                kg.add_event(e)
    kg.add_norms_from_events()
    return kg


def _norm_display(kg: LegalKnowledgeGraph, nid: str) -> str:
    n = kg.norms.get(nid)
    return n.as_text() if n else nid


def main() -> None:
    ap = argparse.ArgumentParser(description="Пайплайн «закон-граф»: предиктивный анализ норм права")
    ap.add_argument("--mode", choices=["synthetic", "corpus"], default="synthetic")
    ap.add_argument("--corpus-root", default=os.environ.get("COURSE_CORPUS_ROOT", ""))
    ap.add_argument("--out", default="runs/law_graph")
    ap.add_argument("--train-ratio", type=float, default=0.6)
    ap.add_argument("--valid-ratio", type=float, default=0.2)
    ap.add_argument("--window", type=int, default=5, help="горизонт прогноза, лет")
    ap.add_argument("--top-k", type=int, default=15)
    ap.add_argument("--backend", default="auto", help="heuristic|auto|pyg")
    ap.add_argument("--export", action="store_true", help="экспортировать датасет JSONL")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("== Этап 1: источник норм и поправок ==")
    if args.mode == "synthetic":
        kg = build_graph_from_synthetic()
        print(f"  режим: synthetic (офлайн-корпус поправок ГК РФ / УК РФ)")
    else:
        if not args.corpus_root:
            print("  [ошибка] --corpus-root не задан (или COURSE_CORPUS_ROOT)")
            return 2
        kg = build_graph_from_corpus(args.corpus_root)
        print(f"  режим: corpus ({args.corpus_root})")

    print(f"  норм: {len(kg.norms)}, законов: {len(kg.laws)}, событий: {len(kg.events)}")

    print("== Этап 2: темпоральный «закон-граф» и хронологическое разбиение ==")
    events = build_event_stream(kg)
    # Хронологическое разбиение применяется ТОЛЬКО к фактическим (связанным во
    # времени) событиям изменения норм. Структурные связи влияния норм
    # (отсылает_к и т.п.) действуют всегда — они переносятся в обучающий граф
    # как контекст и не участвуют в разбиении по времени.
    factual_preds = {
        "изменена", "дополнена", "введена", "изложена_в_новой_редакции",
        "признана_утратившей_силу", "исключена", "уточнена",
    }
    timed = [e for e in events if e.predicate in factual_preds]
    influence = [e for e in events if e.predicate in {
        "отсылает_к", "влечёт_изменение", "требует_приведения_в_соответствие"}]

    train, valid, test = chronological_split(
        timed, train_ratio=args.train_ratio, valid_ratio=args.valid_ratio
    )
    print(f"  факт. событий изменения норм: {len(timed)} "
          f"(train={len(train)} valid={len(valid)} test={len(test)}), "
          f"структурных связей влияния: {len(influence)}")

    train_years = [e.year() for e in train if e.year() > 0]
    train_until = max(train_years) if train_years else 2000
    print(f"  train_until={train_until}, окно прогноза={args.window} лет")

    print("== Этап 3: подготовка датасета (признаки динамики норм до train_until) ==")
    # Для обучения: признаки норм считаются по train-событиям (поправкам до
    # train_until); метка — по тому, изменится ли норма в окне (train_until, +W].
    train_kg = LegalKnowledgeGraph()
    for e in train + influence:
        train_kg.add_event(e)
    train_kg.add_norms_from_events()
    # «будущие» фактические изменения — из valid+test (событий изменений)
    future_events = list(valid + test)

    train_instances = build_task_instances(
        train_kg, train_until=train_until, predict_window=args.window, split="train"
    )
    # присвоить метки по будущим изменениям (фактические изменения в окне)
    future_changed = {e.subject for e in future_events}
    changed_count = 0
    for inst in train_instances:
        if inst.norm_id in future_changed:
            inst.label = 1
            inst.label_source = "factual:" + ";".join(
                f"{e.predicate}@{e.year()}" for e in future_events if e.subject == inst.norm_id
            )
            changed_count += 1
        else:
            inst.label = 0
    print(f"  учебных экземпляров: {len(train_instances)} (из них изменятся: {changed_count})")

    if args.export:
        dump_jsonl([i.model_dump() for i in train_instances], str(out_dir / "dataset.jsonl"))
        (out_dir / "graph.json").write_text(
            json.dumps(to_graph_snapshot(kg), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  датасет экспортирован: {out_dir/'dataset.jsonl'}, граф: {out_dir/'graph.json'}")

    print("== Этап 4: обучение модели ==")
    model = fit_model(train_instances, lr=0.1, epochs=400)
    print("  обученная модель (логистическая регрессия на признаках):")
    print(f"    bias={model.bias:.3f}")
    for name, w in model.weights.items():
        print(f"    {name:28s} w={w:+.3f}")

    print("== Этап 5: прогноз «какие нормы вероятно будут изменены» ==")
    scores = []
    for inst in train_instances:
        s = model.predict_proba(inst)
        inst.predicted_score = s
        scores.append(s)
    ranked = sorted(zip(train_instances, scores), key=lambda kv: kv[1], reverse=True)

    # независимый interpretable-скоринг (без обучения)
    heur = LegalChangeHeuristic(train, config=LegalLinkPredConfig(backend="heuristic"))
    heur_rank = heur.rank(args.top_k)

    print(f"\n  ТОП-{min(args.top_k, len(ranked))} норм по вероятности изменения (обученная модель):")
    for i, (inst, sc) in enumerate(ranked[:args.top_k], 1):
        mark = " [ИЗМЕНИТСЯ]" if inst.label == 1 else ""
        print(f"  {i:2d}. {_norm_display(kg, inst.norm_id):70s} p={sc:.3f}{mark}")

    print(f"\n  ТОП-{min(args.top_k, len(heur_rank))} норм (interpretable-скоринг):")
    for i, (nid, sc) in enumerate(heur_rank[:args.top_k], 1):
        print(f"  {i:2d}. {_norm_display(kg, nid):70s} s={sc:.3f}")

    print("== Этап 6: оценка ==")
    if changed_count > 0:
        met = evaluate_predictions(train_instances, scores)
        print(f"  train AUC-ROC={met['auc_roc']} Prec@5={met['prec_at_5']} "
              f"Prec@10={met['prec_at_10']} Acc={met['accuracy']}")
    else:
        print("  нет фактических изменений в окне прогноза — метрики не считаются")

    # отчёт
    report = {
        "mode": args.mode,
        "norms": len(kg.norms),
        "laws": len(kg.laws),
        "events": len(kg.events),
        "train_until": train_until,
        "window_years": args.window,
        "train_instances": len(train_instances),
        "changed_in_window": changed_count,
        "top_predictions": [
            {"norm_id": i.norm_id, "prob": round(float(s), 4), "label": i.label}
            for i, s in ranked[:args.top_k]
        ],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  отчёт сохранён: {out_dir/'report.json'}")
    print("\nГотово. См. docs/LAW-GRAPH-PIPELINE.md — как интерпретировать результат.")


if __name__ == "__main__":
    raise SystemExit(main())
