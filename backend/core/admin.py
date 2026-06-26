from django.contrib import admin
from core.models import IdempotencyRecord


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ['key', 'user', 'response_status', 'created_at', 'expires_at']
    list_filter = ['response_status', 'created_at']
    search_fields = ['key', 'user__email']
    readonly_fields = ['id', 'created_at']
