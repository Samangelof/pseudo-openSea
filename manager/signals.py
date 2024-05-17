from django.db.models.signals import pre_save
from django.utils.text import slugify
from django.dispatch import receiver

from .models import CreateLink


@receiver(pre_save, sender=CreateLink)
def create_link_slug(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.link)


