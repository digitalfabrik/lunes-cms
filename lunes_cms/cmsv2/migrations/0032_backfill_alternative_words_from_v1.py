import logging

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


# pylint: disable=unused-argument
def backfill_alternative_words(apps, schema_editor):
    """
    Migration 0027 reintroduced alternative words as a cmsv2 model, but only
    created the table - the alternative words that editors had entered in v1
    stayed behind in the cms app and disappeared from the CMS. Copy them over
    so they show up as "So heißt das auch" again.

    Words that already have alternative words are skipped, so anything entered
    by hand since 0027 is neither duplicated nor shadowed.

    :param apps: The configuration of installed applications
    :type apps: ~django.apps.registry.Apps

    :param schema_editor: The database abstraction layer that creates actual SQL code
    :type schema_editor: ~django.db.backends.base.schema.BaseDatabaseSchemaEditor
    """
    Word = apps.get_model("cmsv2", "Word")
    AlternativeWord = apps.get_model("cmsv2", "AlternativeWord")
    V1AlternativeWord = apps.get_model("cms", "AlternativeWord")

    words_by_v1_id = dict(
        Word.objects.filter(v1_id__isnull=False)
        .exclude(alternative_words__isnull=False)
        .values_list("v1_id", "id")
    )
    if not words_by_v1_id:
        logger.info("No words migrated from v1 need their alternative words back.")
        return

    # Reading the v1 table in one pass and matching in memory keeps the query
    # free of an ``IN`` list holding every migrated word.
    restored = []
    for row in V1AlternativeWord.objects.values(
        "document_id", *ALTERNATIVE_WORD_FIELDS
    ).iterator():
        word_id = words_by_v1_id.get(row.pop("document_id"))
        if word_id is not None:
            restored.append(AlternativeWord(word_id=word_id, **row))

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
        ("cmsv2", "0031_remove_alternative_word_permissions"),
    ]

    operations = [
        # Not reversible: once restored, a v1 alternative word cannot be told
        # apart from one an editor typed by hand, so undoing would risk
        # deleting the synonyms this migration exists to bring back.
        migrations.RunPython(
            backfill_alternative_words, migrations.RunPython.noop, elidable=True
        ),
    ]
