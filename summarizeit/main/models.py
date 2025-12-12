from django.db import models

class SummaryCache(models.Model):
    keyword = models.CharField(max_length=255, unique=True, db_index=True)
    summary_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.keyword