import xml.etree.ElementTree as ET
import urllib.request
import ssl
from django.core.management.base import BaseCommand
from app_cart.models import EvropochtaBranch


SOAP_BODY = '''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://w3.org" xmlns:xsd="http://w3.org" xmlns:soap="http://xmlsoap.org">
  <soap:Body>
    <GetProductionInfo xmlns="http://evropochta.by">
      <GetPostalFilters></GetPostalFilters>
    </GetProductionInfo>
  </soap:Body>
</soap:Envelope>'''

ENDPOINT = 'https://evropochta.by'


class Command(BaseCommand):
    help = 'Загрузить отделения Европочты через SOAP API'

    def handle(self, *args, **options):
        self.stdout.write('Запрос к SOAP API Европочты...')

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            ENDPOINT,
            data=SOAP_BODY.encode('utf-8'),
            headers={
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://evropochta.by/GetProductionInfo',
            },
        )

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                raw = resp.read().decode('utf-8')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ошибка SOAP-запроса: {e}'))
            return

        self.stdout.write(f'Получено {len(raw)} байт. Парсинг...')

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            self.stderr.write(self.style.ERROR(f'Ошибка парсинга XML: {e}'))
            return

        ns = {
            'soap': 'http://xmlsoap.org',
            'ep': 'http://evropochta.by',
        }

        branches_data = []
        for elem in root.iter():
            if elem.tag.endswith('PostalInfo') or elem.tag.endswith('ProductionInfo'):
                address_id = ''
                name = ''
                address = ''
                city = ''
                lat = ''
                lon = ''
                is_cash = False
                is_card = False

                for child in elem:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    val = (child.text or '').strip()
                    if tag == 'AddressId':
                        address_id = val
                    elif tag in ('WarehouseName', 'Name'):
                        name = val
                    elif tag == 'Note':
                        address = val
                    elif tag == 'CityName':
                        city = val
                    elif tag == 'Latitude':
                        lat = val
                    elif tag == 'Longitude':
                        lon = val
                    elif tag == 'IsCash':
                        is_cash = val in ('1', 'true', 'True')
                    elif tag == 'IsCard':
                        is_card = val in ('1', 'true', 'True')

                if address_id and name:
                    branches_data.append({
                        'address_id': address_id,
                        'name': name,
                        'address': address,
                        'city': city,
                        'latitude': lat,
                        'longitude': lon,
                        'is_cash': is_cash,
                        'is_card': is_card,
                    })

        if not branches_data:
            self.stdout.write(self.style.WARNING(
                'Прямой парсинг не дал результатов. '
                'Попробуйте: python manage.py fetch_evropochta --raw'
            ))
            return

        created = 0
        updated = 0
        for b in branches_data:
            obj, is_new = EvropochtaBranch.objects.update_or_create(
                address_id=b['address_id'],
                defaults=b,
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Готово: {created} создано, {updated} обновлено, '
            f'всего {EvropochtaBranch.objects.count()} отделений'
        ))
