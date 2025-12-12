from django.contrib import admin
from .models import SummaryCache

@admin.register(SummaryCache)
class SummaryCacheAdmin(admin.ModelAdmin):
    # This controls what columns you see in the list
    list_display = ('keyword', 'summary_text', 'created_at')
    # This adds a search bar to search by keyword
    search_fields = ('keyword',)
