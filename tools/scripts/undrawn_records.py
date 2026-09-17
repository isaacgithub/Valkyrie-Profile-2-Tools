# SPDX-FileCopyrightText: 2026 Valkyrie Profile 2 Translation Tools contributors
# SPDX-License-Identifier: GPL-3.0-only
import csv
import re

from . import einherjar_roster
from .paths import DATA_DIR

STORY_EVENTS_PATH = DATA_DIR / "story-events.csv"
DUPLICATE_LINES_PATH = DATA_DIR / "duplicate-lines.csv"

ITEM_LINE = re.compile(r"^Acquired <PART> (.+)$")

EVENT_MAP_LABEL = "EVENTíMAP"

ROLES = ("join", "item")


def _text(value):
    return " ".join((value or "").split())


def load_story_events(path=None):
    """Return ``{role: {resource: frozenset(names)}}``."""
    source = path or STORY_EVENTS_PATH
    table = {role: {} for role in ROLES}
    try:
        with open(source, encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                resource = (row.get("resource") or "").strip()
                name = (row.get("name") or "").strip()
                role = (row.get("role") or "").strip()
                if resource and name and role in table:
                    table[role].setdefault(resource, set()).add(name)
    except (OSError, csv.Error, UnicodeDecodeError):
        return {role: {} for role in ROLES}
    return {role: {resource: frozenset(names)
                   for resource, names in by_resource.items()}
            for role, by_resource in table.items()}


def duplicate_runs(path=None):
    source = path or DUPLICATE_LINES_PATH
    runs = []
    try:
        with open(source, encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                resource = (row.get("resource") or "").strip()
                drawn_in = (row.get("drawn_in") or "").strip()
                try:
                    first = int((row.get("first_id") or "").strip())
                    last = int((row.get("last_id") or "").strip())
                except ValueError:
                    continue
                if resource and first <= last:
                    runs.append((resource,
                                 frozenset(str(number) for number
                                           in range(first, last + 1)),
                                 drawn_in))
    except (OSError, csv.Error, UnicodeDecodeError):
        return []
    return runs

def load_duplicate_lines(path=None):
    """Return ``{resource: frozenset(message_id)}`` for the unused copies."""
    table = {}
    for resource, ids, _drawn_in in duplicate_runs(path):
        table.setdefault(resource, set()).update(ids)
    return {resource: frozenset(ids) for resource, ids in table.items()}

def _known(table, role):
    return frozenset().union(*table[role].values()) if table[role] else frozenset()


def _resource(rows):
    return next(((row.get("resource") or "").strip()
                 for row in rows if (row.get("resource") or "").strip()), "")


def story_view(rows, table=None):
    """``message_id -> (kind, who, drawn)`` for this scene's story blocks."""
    table = load_story_events() if table is None else table
    resource = _resource(rows)
    view = {}

    joins = einherjar_roster.join_block(rows)
    names = [name for _, name in joins]
    known_cast = _known(table, "join")
    drawn_cast = table["join"].get(resource, frozenset())
    for index in einherjar_roster.story_run(names):
        row, name = joins[index]
        if name in known_cast:
            view[row["message_id"]] = ("join", name, name in drawn_cast)

    known_items = _known(table, "item")
    drawn_items = table["item"].get(resource, frozenset())
    for row in rows:
        if _text(row.get("speaker")):
            continue
        found = ITEM_LINE.match(_text(row.get("original_en")))
        if found and found.group(1) in known_items:
            view[row["message_id"]] = ("item", found.group(1),
                                       found.group(1) in drawn_items)
    return view


def _template_hidden(rows, table=None):
    hidden = {message_id for message_id, (_, _, drawn)
              in story_view(rows, table).items() if not drawn}
    hidden.update(row["message_id"] for row in rows
                  if _text(row.get("original_en")) == EVENT_MAP_LABEL)
    return hidden


def _duplicate_hidden(rows, duplicates=None):
    unused = (load_duplicate_lines() if duplicates is None
              else duplicates).get(_resource(rows), frozenset())
    return {row["message_id"] for row in rows
            if row.get("message_id") in unused}


def hidden_message_ids(rows, table=None, story_table=None,
                       duplicates=None):
    """Every record in ``rows`` this scene never draws, from both models."""
    hidden = einherjar_roster.hidden_message_ids(rows, table)
    hidden.update(_template_hidden(rows, story_table))
    hidden.update(_duplicate_hidden(rows, duplicates))
    return hidden



def reclaimable_message_ids(rows, table=None, story_table=None):
    return einherjar_roster.hidden_message_ids(rows, table) | _template_hidden(
        rows, story_table)

def suppressed_rows(rows, rosters=None, story_table=None):
    """The rows a build must not fill from another sheet's translation."""
    claimed = list(einherjar_roster.suppressed_rows(rows, rosters))
    seen = {id(row) for row in claimed}
    hidden = _template_hidden(rows, story_table)
    claimed.extend(row for row in rows
                   if row.get("message_id") in hidden and id(row) not in seen)
    return claimed


def view(rows, table=None, story_table=None):
    """Both views in one map."""
    merged = dict(einherjar_roster.einherjar_view(rows, table))
    merged.update(story_view(rows, story_table))
    return merged
