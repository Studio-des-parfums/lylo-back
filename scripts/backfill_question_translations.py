"""Rattrapage ponctuel : traduit les questions FR existantes (créées avant la mise en
place de la traduction automatique) vers les 5 autres langues supportées, et crée les
questions/choix sœurs — reproduit exactement ce que fait POST /catalog/questions pour
une nouvelle question FR (voir app/routers/catalog.py), appliqué aux questions déjà en
base qui n'ont pas de translation_group_id.

Usage : python -m scripts.backfill_question_translations [--dry-run]
"""

import argparse
import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import crud
from app.database.connection import AsyncSessionLocal
from app.database.models import Question
from app.services import question_translation_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_question_translations")


async def backfill(dry_run: bool) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Question)
            .options(selectinload(Question.choices), selectinload(Question.groups))
            .where(Question.language == "fr", Question.translation_group_id.is_(None))
        )
        all_questions = result.scalars().all()
        # Ignore les questions orphelines (sans groupe) : jamais posées dans le vrai
        # parcours, donc pas utile de les traduire.
        questions = [q for q in all_questions if q.groups]

    logger.info("Questions FR sans traduction trouvées : %d (dont %d orphelines ignorées)", len(questions), len(all_questions) - len(questions))

    for question in questions:
        group_ids = [g.id for g in question.groups]
        logger.info("— Question #%d: %r (groupes=%s, %d choix)", question.id, question.text, group_ids, len(question.choices))

        if dry_run:
            continue

        async with AsyncSessionLocal() as db:
            translation_group_id = str(uuid.uuid4())

            # Marque la question FR existante comme tête du groupe de traduction.
            await crud.update_question(db, question.id, translation_group_id=translation_group_id)

            question_translations = await question_translation_service.translate_text(question.text)

            sibling_by_lang: dict[str, int] = {}
            for lang, translated_text in question_translations.items():
                sibling = await crud.create_question(
                    db,
                    text=translated_text,
                    language=lang,
                    is_active=question.is_active,
                    group_ids=group_ids,
                    translation_group_id=translation_group_id,
                )
                sibling_by_lang[lang] = sibling.id
                logger.info("  → créée en %s (id=%d): %r", lang, sibling.id, translated_text)

            for choice in question.choices:
                choice_translation_group_id = str(uuid.uuid4())
                await crud.update_choice(db, choice.id, translation_group_id=choice_translation_group_id)

                choice_translations = await question_translation_service.translate_text(choice.text)
                for lang, translated_text in choice_translations.items():
                    sibling_question_id = sibling_by_lang.get(lang)
                    if not sibling_question_id:
                        continue
                    await crud.create_choice(
                        db,
                        question_id=sibling_question_id,
                        text=translated_text,
                        image_url=choice.image_url,
                        language=lang,
                        translation_group_id=choice_translation_group_id,
                    )

    logger.info("Terminé.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Liste les questions concernées sans rien écrire en base")
    args = parser.parse_args()
    asyncio.run(backfill(dry_run=args.dry_run))
