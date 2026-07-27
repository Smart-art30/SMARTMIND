from django.contrib import admin
from .models import School, SchoolClass


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'address', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('created_at',)
    ordering = ('name',)

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'school')
    list_filter = ('school',)
    search_fields = ('name',)