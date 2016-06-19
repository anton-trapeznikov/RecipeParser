from django.core.management.base import BaseCommand
from apps.parser.core import UrlParser

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        parser = UrlParser()
        parser.parse()
        print('Done')