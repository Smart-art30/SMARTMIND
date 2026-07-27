from django.core.management.base import BaseCommand

from library.models import Resource

from smartmind_ai.embed import embed_resource


class Command(BaseCommand):

    help = "Generate embeddings"

    def handle(self, *args, **kwargs):

        resources = Resource.objects.all()

        total = resources.count()

        self.stdout.write(f"Embedding {total} resources...")

        for i, resource in enumerate(resources, start=1):

            embed_resource(resource)

            self.stdout.write(f"{i}/{total}")

        self.stdout.write(
            self.style.SUCCESS("Done.")
        )