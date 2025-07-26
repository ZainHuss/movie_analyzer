from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = 'فحص اتصال قاعدة البيانات'

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS('✅ الاتصال بقاعدة البيانات ناجح!'))
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f'❌ فشل الاتصال: {str(e)}'))