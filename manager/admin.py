from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Worker, CreateLink, Worker, Chat, ReboundTelegram


class WorkerAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_superuser']  # Поля для отображения в списке администраторов
    list_filter = ['is_superuser']  # Фильтры для списка администраторов
    search_fields = ['email', 'id_telegram']  # Поля, по которым можно выполнять поиск


class LinkAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("link",)}


admin.site.register(Worker, WorkerAdmin)
admin.site.register(CreateLink, LinkAdmin)
admin.site.register(Chat)
admin.site.register(ReboundTelegram)
