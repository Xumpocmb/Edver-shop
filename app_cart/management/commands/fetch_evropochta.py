import json
import ssl
import urllib.request

from django.core.management.base import BaseCommand

from app_cart.models import EvropochtaBranch

ENDPOINT = 'https://evropochta.by/rest/Json'
DEFAULT_METHOD = 'Postal.OfficesOut'
DEFAULT_SERVICE_NUMBER = 'E811AE79-DFDE-4F85-8715-DD3A8308707E'
USER_AGENT = 'Mozilla/5.0'


class Command(BaseCommand):
    help = 'Обновить отделения Европочты из JSON API evropochta.by'

    def add_arguments(self, parser):
        parser.add_argument(
            '--what',
            default=DEFAULT_METHOD,
            help='Имя метода JSON API (по умолчанию Postal.OfficesOut)',
        )
        parser.add_argument(
            '--keep-stale',
            action='store_true',
            help='Не удалять отделения, которых больше нет в API',
        )

    def handle(self, *args, **options):
        method = options['what']
        self.stdout.write(f'Запрос {method} к {ENDPOINT}...')

        table = self.fetch_offices(method, DEFAULT_SERVICE_NUMBER)
        self.stdout.write(f'Получено {len(table)} отделений. Обновление БД...')

        branches = [self.to_branch(row) for row in table]
        created = 0
        updated = 0
        for b in branches:
            _, is_new = EvropochtaBranch.objects.update_or_create(
                address_id=b['address_id'],
                defaults=b,
            )
            if is_new:
                created += 1
            else:
                updated += 1

        if not options['keep_stale']:
            stale = EvropochtaBranch.objects.exclude(
                address_id__in=[b['address_id'] for b in branches]
            )
            stale_count = stale.count()
            stale.delete()
        else:
            stale_count = 0

        self.stdout.write(self.style.SUCCESS(
            f'Готово: {created} создано, {updated} обновлено, '
            f'{stale_count} удалено как устаревшие, '
            f'всего {EvropochtaBranch.objects.count()} отделений'
        ))

    def fetch_offices(self, method, service_number):
        payload = {
            'CRC': '',
            'Packet': {
                'MethodName': method,
                'JWT': None,
                'ServiceNumber': service_number,
                'Data': {},
            },
        }
        req = urllib.request.Request(
            f'{ENDPOINT}?What={method}',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': USER_AGENT,
                'Origin': 'https://evropochta.by',
                'Referer': 'https://evropochta.by/about/offices/',
            },
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            raw = resp.read().decode('utf-8')

        try:
            data = json.loads(raw)
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f'Ответ не является JSON: {e}'))
            raise SystemExit(1)

        table = data.get('Table') or []
        if not table:
            self.stderr.write(self.style.ERROR(
                f'API не вернул отделений: {raw[:300]}'
            ))
            raise SystemExit(1)
        return table

    @staticmethod
    def _field(row, key, default=''):
        value = row.get(key)
        return (value or default).strip()

    @classmethod
    def to_branch(cls, row):
        prefix = cls._field(row, 'Address4NamePrefix')
        street = cls._field(row, 'Address4Name')
        house = cls._field(row, 'Address3Name')
        address_parts = [part for part in (
            cls._field(row, 'Address6Name'),
            f'{prefix} {street}'.strip(),
            house,
        ) if part]
        return {
            'address_id': cls._field(row, 'WarehouseId'),
            'name': cls._field(row, 'WarehouseName'),
            'address': ', '.join(address_parts),
            'city': cls._field(row, 'Address7Name'),
            'latitude': cls._field(row, 'Latitude'),
            'longitude': cls._field(row, 'Longitude'),
        }