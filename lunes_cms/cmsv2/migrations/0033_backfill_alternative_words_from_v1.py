import logging
from collections import defaultdict

from django.db import migrations

logger = logging.getLogger(__name__)

#: The fields an alternative word carries over unchanged from v1
ALTERNATIVE_WORD_FIELDS = (
    "alt_word",
    "grammatical_gender",
    "singular_article",
    "plural",
    "plural_article",
)


def normalized(alt_word):
    """
    The form an alternative word is compared in, so that a synonym an editor
    re-typed with a different case or spacing still counts as the same one.

    :param alt_word: The alternative word to normalize
    :type alt_word: str

    :return: The normalized alternative word
    :rtype: str
    """
    return " ".join(alt_word.split()).casefold()


# pylint: disable=unused-argument
def backfill_alternative_words(apps, schema_editor):
    """
    Migration 0027 reintroduced alternative words as a cmsv2 model, but only
    created the table - the alternative words that editors had entered in v1
    stayed behind in the cms app and disappeared from the CMS. Copy them over
    so they show up as "So heißt das auch" again.

    Alternative words are matched one by one, so a synonym an editor already
    re-entered by hand since 0027 is neither duplicated nor shadowed, while
    the remaining synonyms of that same word still come back.

    :param apps: The configuration of installed applications
    :type apps: ~django.apps.registry.Apps

    :param schema_editor: The database abstraction layer that creates actual SQL code
    :type schema_editor: ~django.db.backends.base.schema.BaseDatabaseSchemaEditor
    """
    Word = apps.get_model("cmsv2", "Word")
    AlternativeWord = apps.get_model("cmsv2", "AlternativeWord")
    V1AlternativeWord = apps.get_model("cms", "AlternativeWord")

    # ``v1_id`` is not unique, so a v1 document may map to more than one word.
    words_by_v1_id = defaultdict(list)
    for v1_id, word_id in Word.objects.filter(v1_id__isnull=False).values_list(
        "v1_id", "id"
    ):
        words_by_v1_id[v1_id].append(word_id)
    if not words_by_v1_id:
        logger.info("No words migrated from v1 need their alternative words back.")
        return

    alternatives_by_word = defaultdict(set)
    for word_id, alt_word in AlternativeWord.objects.values_list("word_id", "alt_word"):
        alternatives_by_word[word_id].add(normalized(alt_word))

    # Reading the v1 table in one pass and matching in memory keeps the query
    # free of an ``IN`` list holding every migrated word.
    restored = []
    for row in V1AlternativeWord.objects.values(
        "document_id", *ALTERNATIVE_WORD_FIELDS
    ).iterator():
        alt_word = normalized(row["alt_word"])
        for word_id in words_by_v1_id.get(row["document_id"], ()):
            if alt_word in alternatives_by_word[word_id]:
                continue
            alternatives_by_word[word_id].add(alt_word)
            restored.append(
                AlternativeWord(
                    word_id=word_id,
                    **{field: row[field] for field in ALTERNATIVE_WORD_FIELDS},
                )
            )

    AlternativeWord.objects.bulk_create(restored, batch_size=500)
    # This runs unattended on deploy, so without a count a restore that found
    # nothing would look exactly like a successful one.
    logger.info(
        "Restored %s alternative words from v1 across %s words.",
        len(restored),
        len({alternative.word_id for alternative in restored}),
    )


class Migration(migrations.Migration):
    """
    Migration file to restore the alternative words entered in v1.
    """

    dependencies = [
        ("cms", "0015_add_grammatical_gender_fields"),
        ("cmsv2", "0032_review_unit_word"),
    ]

    operations = [
        # Not reversible: once restored, a v1 alternative word cannot be told
        # apart from one an editor typed by hand, so undoing would risk
        # deleting the synonyms this migration exists to bring back.
        migrations.RunPython(
            backfill_alternative_words, migrations.RunPython.noop, elidable=True
        ),
    ]
