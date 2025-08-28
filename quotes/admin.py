from django.contrib import admin
from .models import Source, Quote


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    search_fields = ("name",)
    list_filter = ("type",)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        "short_text",
        "source",
        "weight",
        "views",
        "likes",
        "dislikes",
        "created_at",
    )
    list_select_related = ("source",)
    search_fields = ("text", "source__name")
    list_filter = ("source__type", "source")
    ordering = ("-likes",)
    autocomplete_fields = ("source",)

    @admin.display(description="Text")
    def short_text(self, obj: Quote) -> str:
        return (obj.text[:80] + "…") if len(obj.text) > 80 else obj.text


# Register your models here.
