"""Локальная база правил и проверка комплектности без внешних языковых моделей."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class RuleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Clause(RuleModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    topics: list[str] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)
    url: str | None = None


class FieldRule(RuleModel):
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    reference: str = Field(min_length=1)
    kind: Literal["text", "date", "boolean"] = "text"
    must_be_true: bool = False

    @model_validator(mode="after")
    def validate_boolean_requirement(self):
        if self.must_be_true and self.kind != "boolean":
            raise ValueError("must_be_true допустим только для boolean")
        return self


class DateOrder(RuleModel):
    start: str
    end: str
    reference: str


class DocumentRule(RuleModel):
    label: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    required_fields: list[FieldRule] = Field(default_factory=list)
    date_orders: list[DateOrder] = Field(default_factory=list)


def normalize(value: str) -> str:
    return re.sub(r"[\W_]+", " ", value.casefold().replace("ё", "е")).strip()


class KnowledgeBase(RuleModel):
    title: str = "Положение вуза"
    source_type: str = "положение"
    # Стартовая база из презентации явно отличается от нормативного Положения.
    scope_note: str = ""
    clauses: list[Clause] = Field(default_factory=list)
    document_types: dict[str, DocumentRule] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self):
        ids = [clause.id for clause in self.clauses]
        if any(not clause.id.strip() or not clause.text.strip() for clause in self.clauses):
            raise ValueError("Пункт и его текст не должны быть пустыми")
        if len(ids) != len(set(ids)):
            raise ValueError("Идентификаторы пунктов должны быть уникальны")
        type_names: set[str] = set()
        for name, document in self.document_types.items():
            for alias in {normalize(v) for v in [name, document.label, *document.aliases]}:
                if not alias:
                    raise ValueError("Название или alias типа документа не должны быть пустыми")
                if alias in type_names:
                    raise ValueError(f"Неоднозначное название типа документа: {alias}")
                type_names.add(alias)
            names = [rule.name for rule in document.required_fields]
            if len(names) != len(set(names)):
                raise ValueError(f"Повторяющиеся поля в типе {name}")
            aliases: set[str] = set()
            for rule in document.required_fields:
                if rule.reference not in ids:
                    raise ValueError(f"Неизвестный пункт {rule.reference} для {name}.{rule.name}")
                for alias in {normalize(v) for v in [rule.name, rule.label, *rule.aliases]}:
                    if not alias:
                        raise ValueError("Название или alias поля не должны быть пустыми")
                    if alias in aliases:
                        raise ValueError(f"Неоднозначное имя поля: {name}.{alias}")
                    aliases.add(alias)
            for order in document.date_orders:
                dates = {rule.name for rule in document.required_fields if rule.kind == "date"}
                if order.start not in dates or order.end not in dates or order.reference not in ids:
                    raise ValueError(f"Некорректное правило порядка дат для {name}")
        return self


def load_knowledge_base(path: Path) -> KnowledgeBase:
    """Ошибки конфигурации останавливают запуск; отсутствующую базу обрабатывает API."""
    return KnowledgeBase.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))


def document_rule(base: KnowledgeBase, document_type: str | None) -> tuple[str | None, DocumentRule | None]:
    normalized = normalize(document_type or "")
    if not normalized:
        return None, None
    for key, rule in base.document_types.items():
        if normalized in {normalize(v) for v in [key, rule.label, *rule.aliases]}:
            return key, rule
    return None, None


MISSING_VALUES = {"", "не найдено", "не найден", "не найдена", "не указано", "нет данных", "null", "none", "unknown", "n a"}
TRUE_VALUES = {"да", "есть", "true", "1", "присутствует", "найдено", "найдена", "найден"}
FALSE_VALUES = {"нет", "false", "0", "отсутствует", "не обнаружено", "не обнаружена"}


def unwrap(value: JsonValue) -> JsonValue:
    return value.get("value") if isinstance(value, dict) and "value" in value else value


def is_missing(value: JsonValue, kind: str = "text") -> bool:
    missing = MISSING_VALUES | ({"нет", "отсутствует", "отсутствуют"} if kind != "boolean" else set())
    return value is None or (isinstance(value, str) and normalize(value) in missing)


def as_boolean(value: JsonValue) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = normalize(value)
        if text in TRUE_VALUES:
            return True
        if text in FALSE_VALUES:
            return False
    return None


def as_date(value: JsonValue):
    if not isinstance(value, str):
        return None
    for pattern in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            pass
    return None


def field_value(fields: dict[str, JsonValue], rule: FieldRule) -> tuple[JsonValue, bool]:
    """При расхождении канонического имени и alias не выбираем значение молча."""
    aliases = {normalize(v) for v in [rule.name, rule.label, *rule.aliases]}
    values = [unwrap(value) for key, value in fields.items() if normalize(key) in aliases]
    if not values:
        return None, False
    # Отсутствующая OCR-кандидатура не должна затереть найденную.
    found = [value for value in values if not is_missing(value, rule.kind)]
    if not found:
        return None, False
    def comparable(value):
        if rule.kind == "boolean":
            parsed = as_boolean(value)
            return parsed if parsed is not None else value
        if rule.kind == "date":
            return as_date(value) or value
        return normalize(value) if isinstance(value, str) else value
    first = comparable(found[0])
    return found[0], any(comparable(value) != first for value in found[1:])


def source(base: KnowledgeBase, clause: Clause) -> dict:
    prefix = f"п. {clause.id}" if re.fullmatch(r"\d+(?:\.\d+)*\.?", clause.id) else clause.id
    return {"type": base.source_type, "reference": f"{prefix} — {base.title}", "url": clause.url}


def check_document(base: KnowledgeBase, doc_type: str | None, fields: dict[str, JsonValue]) -> tuple[dict, list[dict], str]:
    _, rule = document_rule(base, doc_type)
    if rule is None or not rule.required_fields:
        return {"status": "unknown", "missing_fields": [], "issues": [
            "Для этого типа документа не загружены требования к обязательным полям."
        ]}, [], "Недостаточно данных для проверки комплектности документа."
    missing, issues, references = [], [], []
    values = {}
    for requirement in rule.required_fields:
        value, conflict = field_value(fields, requirement)
        values[requirement.name] = value
        references.append(requirement.reference)
        if is_missing(value, requirement.kind):
            missing.append(requirement.name)
        elif conflict:
            issues.append(f"{requirement.label}: распознаны противоречивые значения.")
        elif requirement.kind == "date" and as_date(value) is None:
            issues.append(f"{requirement.label}: некорректная дата; ожидается ДД.ММ.ГГГГ или ГГГГ-ММ-ДД.")
        elif requirement.kind == "boolean":
            boolean = as_boolean(value)
            if boolean is None:
                issues.append(f"{requirement.label}: не удалось определить наличие (есть/нет).")
            elif requirement.must_be_true and not boolean:
                issues.append(f"{requirement.label}: отсутствует.")
        elif requirement.kind == "text" and (isinstance(value, (dict, list, bool)) or str(value).strip() == ""):
            issues.append(f"{requirement.label}: некорректное значение поля.")
    for order in rule.date_orders:
        start, end = as_date(values.get(order.start)), as_date(values.get(order.end))
        if start and end and start > end:
            labels = {field.name: field.label for field in rule.required_fields}
            issues.append(f"{labels[order.start]} не может быть позже поля «{labels[order.end]}».")
            references.append(order.reference)
    status = "incomplete" if missing or issues else "complete"
    if status == "complete":
        summary = f"Документ в порядке по проверке комплектности: «{rule.label}» содержит все поля из загруженных требований."
    else:
        parts = ["Чего-то не хватает или есть ошибки в полях документа."]
        if missing:
            labels = {field.name: field.label for field in rule.required_fields}
            parts.append("Не найдены обязательные поля: " + ", ".join(labels[name] for name in missing) + ".")
        parts.extend(issues)
        summary = " ".join(parts)
    clauses = {clause.id: clause for clause in base.clauses}
    sources = [source(base, clauses[reference]) for reference in dict.fromkeys(references)]
    return {"status": status, "missing_fields": missing, "issues": issues}, sources, summary


STOP_WORDS = set("а без бы был была были в во вот вы да для до его ее если есть же за и из или их к как какой какая какие какое ли либо мне можно мой мы на надо наш не него нее но о об он она они от по под при про с со так такой там то у уже что чтобы это этот эта эти я документ документа документы студент студента пожалуйста подскажите скажите".split())
SEARCH_FILLERS = set("нужен нужна нужно нужны необходим необходимо необходимы требуется требуются содержать содержит перечислены указаны указано".split())
SUFFIXES = ("иями", "ение", "ения", "остью", "овать", "ивать", "иться", "аться", "ами", "ями", "ого", "ему", "ому", "ыми", "ими", "ать", "ять", "ить", "ия", "ий", "ие", "ый", "ой", "ая", "ое", "ые", "ов", "ев", "ам", "ям", "ах", "ях", "ом", "ем", "ет", "ут", "ют", "а", "я", "ы", "и", "у", "ю", "е", "о")


def tokens(text: str) -> set[str]:
    result = set()
    for word in normalize(text).split():
        if word in STOP_WORDS or word in SEARCH_FILLERS or len(word) < 3:
            continue
        word = {"когда": "срок", "подавать": "подача", "подать": "подача"}.get(word, word)
        for suffix in SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                word = word[:-len(suffix)]
                break
        result.add(word)
    return result


def retrieve(base: KnowledgeBase, question: str, doc_type: str | None) -> list[Clause]:
    query = tokens(question)
    if not query:
        return []
    ranked = []
    for clause in base.clauses:
        if doc_type and clause.document_types and doc_type not in clause.document_types:
            continue
        topic = tokens(" ".join(clause.topics))
        content = tokens(clause.text)
        overlap = query & (topic | content)
        # Частичное совпадение вроде «стоимость обучения» / «справка об обучении»
        # не является ответом на вопрос о стоимости.
        coverage = len(overlap) / len(query)
        if coverage < 1:
            continue
        ranked.append((coverage + len(query & topic) / len(query), clause))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [clause for _, clause in ranked[:3]]


def is_completeness_question(question: str) -> bool:
    question = normalize(question)
    if re.search(r"стоим|цен[аыуе]|оплат|деньг|рубл|продл|стипенд|общежит|подлинн|действител|балл|срок.*подач", question):
        return False
    if question in {"проверь", "проверить", "хватит ли", "достаточно ли", "подходит ли",
                    "все ли в порядке", "документ в порядке", "чего не хватает", "что исправить"}:
        return True
    if re.search(r"комплектност|обязательн.*пол|пол.*обязательн|все ли.*(?:пол|заполн)|правильн.*заполн|заполн.*правильн|чего.*не хватает|каких.*пол.*не хватает", question):
        return True
    if re.search(r"(?:хватит|достаточно|подходит|подойдет).*(?:справк|документ|заявлен)", question):
        return True
    return bool(re.fullmatch(r"(?:проверь|проверьте|проверить|проверка) (?:этот |эту |мой |мою )?(?:документ|справку|заявление)(?: пожалуйста)?", question))


def asks_for_field(question: str, field: FieldRule) -> bool:
    if re.search(r"нуж|необход|треб|долж|ставить|постав|кто|кем|сколько|стоим|цен[аыуе]|разреш|можно|зачем|обязательн", normalize(question)):
        return False
    query = tokens(question) - tokens("поле значение указан указана написан написана записан записана распознан распознана найден найдена назови покажи")
    labels = [field.label, field.name.replace("_", " "), *field.aliases]
    return bool(query) and any(query == tokens(label) for label in labels)


def contextual_question(question: str, history: list) -> str:
    # История уточняет только короткий отсылочный вопрос, а не заменяет новый вопрос.
    if normalize(question) in {"почему", "почему так", "что именно", "какие именно", "а подробнее", "подробнее", "на каком основании", "что исправить"}:
        for message in reversed(history):
            if message.role == "user":
                return f"{message.content} {question}"
    return question


def answer_question(base: KnowledgeBase, question: str, document, history: list) -> dict:
    question = contextual_question(question, history)
    key, rule = document_rule(base, document.type if document else None)
    verification, sources, summary = None, [], ""
    if document is not None:
        verification, sources, summary = check_document(base, document.type, document.fields)

    # Явное упоминание другого типа в новом вопросе важнее старого вложения.
    query_terms = tokens(question)
    requested_types = [name for name, config in base.document_types.items()
                       if any((terms := tokens(label)) and terms <= query_terms
                              for label in [config.label, *config.aliases])]
    search_type = requested_types[0] if len(requested_types) == 1 else (None if requested_types else key)
    clauses = retrieve(base, question, search_type)
    parts = []
    # Вопрос о конкретном поле можно ответить по документу и без нормативной базы.
    if document is not None and rule is not None and not is_completeness_question(question):
        for field in rule.required_fields:
            if not asks_for_field(question, field):
                continue
            value, conflict = field_value(document.fields, field)
            if conflict:
                text = "распознаны противоречивые значения"
            elif is_missing(value, field.kind):
                text = "не найдено"
            elif field.kind == "boolean" and as_boolean(value) is not None:
                text = "есть" if as_boolean(value) else "нет"
            else:
                text = str(value)
            parts.append(f"По данным документа: {field.label} — {text}.")
            sources.append({"type": "документ", "reference": f"Поле «{field.label}»", "url": None})

    if clauses:
        parts.append("В загруженных правилах найдены пункты:\n" + "\n".join(
            f"{clause.id}: {clause.text}" for clause in clauses
        ))
        sources.extend(source(base, clause) for clause in clauses)
    elif not parts and not (document is not None and is_completeness_question(question) and verification["status"] != "unknown"):
        parts.append("Ответа нет: в загруженных правилах и полях документа не найдено достаточно информации для ответа на этот вопрос. Обратитесь в деканат.")

    if summary:
        parts.append(summary)
    if base.scope_note and (clauses or (verification and verification["status"] != "unknown")):
        parts.append(base.scope_note)
    if document is not None:
        parts.append("Проверка не означает принятие документа. Окончательное решение принимает сотрудник деканата.")
    unique_sources = {item["reference"]: item for item in sources}
    return {"answer": "\n\n".join(parts), "sources": list(unique_sources.values()), "verification": verification}
