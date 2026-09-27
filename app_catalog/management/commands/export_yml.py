"""Выгрузка YML-фида товаров для Яндекс Маркета."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from app_catalog import yml_feed


class Command(BaseCommand):
    help = "Собирает YML-фид товаров для Яндекс Маркета"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            help="Путь к файлу (по умолчанию media/feeds/edver-shop.yml)",
        )

    def handle(self, *args, **options):
        text, stats = yml_feed.build_feed()

        if options["output"]:
            path = Path(options["output"])
        else:
            path = Path(settings.MEDIA_ROOT) / "feeds" / "edver-shop.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

        self.stdout.write(
            f"Товаров: {stats['products']}, предложений: {stats['offers']}"
        )
        if stats["offers_without_picture"]:
            self.stdout.write(self.style.WARNING(
                f"Без подходящих фото: {stats['offers_without_picture']} "
                "(Яндекс не принимает SVG)"
            ))
        if stats["categories_without_market_id"]:
            self.stdout.write(self.style.WARNING(
                "Не заполнен ID категории в Яндекс Маркете: "
                + ", ".join(stats["categories_without_market_id"])
            ))
        self.stdout.write(self.style.SUCCESS(f"Файл: {path}"))
