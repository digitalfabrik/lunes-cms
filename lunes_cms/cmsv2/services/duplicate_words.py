"""
Detecting duplicate vocabulary within a profession (issue #531).

A "duplicate" here means two or more *distinct* ``Word`` rows sharing the
same text. Each duplicate group is reported once, together with every job
it's reachable from — not once per job — since the same unit (and therefore
the same duplicate pair) can belong to several jobs at once, and repeating
the group under each job separately would just show the same words over and
over. A word that isn't linked to any unit/job yet (freshly created, not yet
assigned) has no job of its own, so it's folded into the job(s) its
same-text sibling(s) belong to instead of being invisible until someone
links it. If every occurrence of a text is such an unassigned word, the
group has no job at all ("not assigned to a profession").

Two things are deliberately *not* flagged:

- The same word text appearing in different jobs, with no unassigned word
  involved — that's normal reuse (e.g. "Hammer" legitimately taught in both
  "Tischler" and "Maurer").
- One ``Word`` row linked to two units of the *same* job — that's one word
  taught in two contexts, not a data-quality problem.

A group a content manager has explicitly reviewed and accepted as an
intentional duplicate (``AcceptedWordDuplicate``) is excluded too, so it
doesn't keep reappearing once someone has decided it's fine as-is.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..models import AcceptedWordDuplicate, Job, Word
from .remove_duplicate_word import completeness_score


@dataclass
class DuplicateWordGroup:
    """One duplicate-vocabulary group: every ``Word`` row sharing the same text and unit context."""

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


def _build_groups() -> dict[tuple[str, frozenset[int]], set[int]]:
    """
    Returns ``{(word_text, member_ids): job_ids}`` — each distinct duplicate
    group (by text and exact set of words involved) mapped to every job it's
    reachable from. An empty job-id set means every member is unassigned.
    Groups accepted as intentional duplicates are left out entirely.
    """
    job_ids_by_word_id = _job_ids_by_word_id()
    accepted_member_id_sets = _accepted_member_id_sets()
    groups: dict[tuple[str, frozenset[int]], set[int]] = defaultdict(set)

    for word_text, word_ids in _word_ids_by_text().items():
        if len(word_ids) < 2:
            continue
        orphan_ids = [wid for wid in word_ids if not job_ids_by_word_id.get(wid)]
        all_job_ids: set[int] = set()
        for wid in word_ids:
            all_job_ids |= job_ids_by_word_id.get(wid, set())

        if not all_job_ids:
            # Every occurrence is unassigned — no job to attach this to.
            members = frozenset(word_ids)
            if members not in accepted_member_id_sets:
                groups[(word_text, members)] |= set()
            continue

        for job_id in all_job_ids:
            members = frozenset(
                [wid for wid in word_ids if job_id in job_ids_by_word_id.get(wid, ())]
                + orphan_ids
            )
            if len(members) >= 2 and members not in accepted_member_id_sets:
                groups[(word_text, members)].add(job_id)

    return groups


def duplicate_word_group_count() -> int:
    """Cheap count of duplicate groups."""
    return len(_build_groups())


def find_duplicate_word_groups() -> list[DuplicateWordGroup]:
    """
    Find every duplicate-vocabulary group, one entry each (not repeated per
    job), sorted by the jobs involved (unassigned last) then word text.
    Words within a group are ordered by completeness (most complete first),
    as a hint for which one to keep.
    """
    groups = _build_groups()

    all_word_ids = {wid for (_, members) in groups for wid in members}
    words_by_id = {word.pk: word for word in Word.objects.filter(pk__in=all_word_ids)}

    all_job_ids = {jid for job_ids in groups.values() for jid in job_ids}
    jobs_by_id = {job.pk: job for job in Job.objects.filter(pk__in=all_job_ids)}

    result = []
    for (word_text, members), job_ids in groups.items():
        words = sorted(
            (words_by_id[wid] for wid in members),
            key=completeness_score,
            reverse=True,
        )
        job_names = sorted(jobs_by_id[jid].name for jid in job_ids)
        result.append(
            DuplicateWordGroup(word_text=word_text, words=words, job_names=job_names)
        )

    result.sort(key=lambda g: (not g.job_names, ", ".join(g.job_names), g.word_text))
    return result
