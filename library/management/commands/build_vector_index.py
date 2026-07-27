from django.core.management.base import BaseCommand
from smartmind_ai.build_index import build_index


class Command(BaseCommand):
    help = "Build SmartMind Vector Index"

    def handle(self, *args, **kwargs):
        build_index()