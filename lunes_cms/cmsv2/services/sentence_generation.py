"""
Example sentence generation for Word objects via OpenAI.
"""

from django.conf import settings

from ..utils import get_openai_client


def build_example_sentence_prompt(word: str, job: str, unit: str | None = None) -> str:
    """
    Build the German prompt for generating an example sentence.

    Args:
        word: The vocabulary term the sentence is about
        job: The job (or comma-separated jobs) providing the professional context
        unit: Optional title of the learning unit for unit<>word relations

    Returns:
        str: The prompt to send to OpenAI
    """
    context = f"im Rahmen des Berufs {job}"
    if unit:
        context += f" und der Lerneinheit {unit}"
    return (
        "Für eine interaktive Übung in einer Vokabel-Lern-App benötige ich "
        f"einen Beispielsatz für den Fachbegriff {word} {context}. "
        "Es können Aussagesätze, Fragesätze oder Aufforderungssätze sein. "
        "Der Fachbegriff soll nicht immer am Satzanfang stehen. "
        "Der Beispielsatz sollte aus dem Arbeitsalltag des vorher genannten "
        "Berufes stammen. Das Sprachniveau der Sätze soll hauptsächlich für "
        "Lernende mit Deutsch als Zweitsprache (B1) passen, aber es dürfen "
        "auch ein paar B2 Niveau Sätze sein. Sätze eher kürzer halten "
        "(5-10 Wörter). "
        "Antworte ausschließlich mit dem Beispielsatz, ohne Anführungszeichen "
        "und ohne zusätzliche Erklärungen."
    )


def openai_example_sentence(word: str, job: str, unit: str | None = None) -> str:
    """
    Generate a single example sentence for a vocabulary term via OpenAI.

    Args:
        word: The vocabulary term the sentence is about
        job: The job (or comma-separated jobs) providing the professional context
        unit: Optional title of the learning unit for unit<>word relations

    Returns:
        str: The generated example sentence

    Raises:
        ValueError: If OpenAI returns an empty response
    """
    client = get_openai_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_TEXT_MODEL,
        messages=[
            {
                "role": "user",
                "content": build_example_sentence_prompt(word, job, unit),
            }
        ],
    )
    sentence = (response.choices[0].message.content or "").strip()
    # The prompt asks for the bare sentence, but strip stray quotes anyway.
    sentence = sentence.strip("\"'„“‚‘»«").strip()
    if not sentence:
        raise ValueError("OpenAI returned an empty example sentence.")
    return sentence
