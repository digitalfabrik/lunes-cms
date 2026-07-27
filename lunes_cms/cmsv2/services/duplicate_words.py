"""
Detecting duplicate vocabulary across the vocabulary base (issue #531).

A "duplicate" here means two or more *distinct* ``Word`` rows sharing the
same text — regardless of which unit or job each row is linked to. Each
duplicate group is reported once, together with every job it's reachable
from (a word can be linked to units belonging to several jobs at once, and
repeating the group once per job would just show the same words over and
over). A word that isn't linked to any unit/job yet (freshly created, not
yet assigned) has no job of its own; it still shows up in its same-text
sibling(s)' group. If every occurrence of a text is such an unassigned
word, the group has no job at all ("not assigned to a profession").

One ``Word`` row linked to two units — whether of the same job or of
different jobs — is *not* flagged by itself: a duplicate always requires
two distinct ``Word`` rows, and one row taught in several contexts is not a
data-quality problem.

Same-text words that belong to different, unrelated jobs (e.g. "Hammer"
taught in both "Tischler" and "Maurer") are shown here too, since that can
either be legitimate reuse or an accidental copy — the content manager
decides. A group explicitly reviewed and accepted as an intentional
duplicate (``AcceptedWordDuplicate``) is excluded from then on, so it
doesn't keep reappearing once someone has decided it's fine as-is.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..models import AcceptedWordDuplicate, Job, Word
from .remove_duplicate_word import completeness_score


@dataclass
class DuplicateWordGroup:
    """One duplicate-vocabulary group: every ``Word`` row sharing the same text."""

    word_text: str
    words: list[Word]
    #: Names of every job this group is reachable from, sorted; empty if none (unassigned bucket).
    job_names: list[str]


def _job_ids_by_word_id() -> dict[int, set[int]]:
    """Every Word id mapped to the set of job ids it's reachable from via a unit (possibly empty)."""
    job_ids: dict[int, set[int]] = defaultdict(set)
    for word_id, job_id in Word.objects.filter(units__jobs__isnull=False).values_list(
        "id", "units__jobs"
    ):
        job_ids[word_id].add(job_id)
    return job_ids


def _word_ids_by_text() -> dict[str, list[int]]:
    ids_by_text: dict[str, list[int]] = defaultdict(list)
    for word_id, text in Word.objects.values_list("id", "word"):
        ids_by_text[text].append(word_id)
    return ids_by_text


def _accepted_member_id_sets() -> set[frozenset[int]]:
    """Every group of words a content manager has already accepted as an intentional duplicate."""
    return {
        frozenset(accepted.words.values_list("id", flat=True))
        for accepted in AcceptedWordDuplicate.objects.prefetch_related("words")
    }


def _build_groups() -> dict[str, frozenset[int]]:
    """
    Returns ``{word_text: member_ids}`` — every word text with two or more
    distinct ``Word`` rows, regardless of which unit or job each is linked
    to. Groups accepted as intentional duplicates are left out entirely.
    """
    accepted_member_id_sets = _accepted_member_id_sets()
    groups: dict[str, frozenset[int]] = {}

    for word_text, word_ids in _word_ids_by_text().items():
        if len(word_ids) < 2:
            continue
        members = frozenset(word_ids)
        if members not in accepted_member_id_sets:
            groups[word_text] = members

    return groups


def duplicate_word_group_count() -> int:
    """Cheap count of duplicate groups."""
    return len(_build_groups())


def find_duplicate_word_groups() -> list[DuplicateWordGroup]:
    """
    Find every duplicate-vocabulary group, sorted by the jobs involved
    (unassigned last) then word text. Words within a group are ordered by
    completeness (most complete first), as a hint for which one to keep.
    """
    groups = _build_groups()
    job_ids_by_word_id = _job_ids_by_word_id()

    all_word_ids = {wid for members in groups.values() for wid in members}
    words_by_id = {word.pk: word for word in Word.objects.filter(pk__in=all_word_ids)}

    all_job_ids = {
        jid
        for members in groups.values()
        for wid in members
        for jid in job_ids_by_word_id.get(wid, ())
    }
    jobs_by_id = {job.pk: job for job in Job.objects.filter(pk__in=all_job_ids)}

    result = []
    for word_text, members in groups.items():
        words = sorted(
            (words_by_id[wid] for wid in members),
            key=completeness_score,
            reverse=True,
        )
        job_ids = {jid for wid in members for jid in job_ids_by_word_id.get(wid, ())}
        job_names = sorted(jobs_by_id[jid].name for jid in job_ids)
        result.append(
            DuplicateWordGroup(word_text=word_text, words=words, job_names=job_names)
        )

    result.sort(key=lambda g: (not g.job_names, ", ".join(g.job_names), g.word_text))
    return result
