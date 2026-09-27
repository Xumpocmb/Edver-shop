"""Генерация превью для уже загруженных файлов (в media/)."""

from django.core.management.base import BaseCommand

from app_media import processing
from app_media.registry import iter_watched


class Command(BaseCommand):
    help = "Создаёт превью и WebP-версии для уже загруженных изображений"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Перезаписать существующие превью (например, после смены качества)",
        )

    def handle(self, *args, **options):
        force = options["force"]
        verbose = options["verbosity"] > 0
        total = 0
        for model, field_name, profile in iter_watched():
            queryset = model.objects.exclude(**{f"{field_name}__isnull": True, f"{field_name}__exact": ""})
            total_files = queryset.count()
            done = 0
            for instance in queryset.iterator():
                if processing.generate(getattr(instance, field_name), profile, force=force):
                    done += 1
            total += done
            if verbose:
                self.stdout.write(
                    f"{model._meta.verbose_name_plural}: превью создано для {done} из {total_files}"
                )
        if verbose:
            self.stdout.write(self.style.SUCCESS(f"Готово, обработано файлов: {total}"))
