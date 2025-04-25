from django.contrib import admin
from .models import Listing, ListingSlot, Review


class ListingSlotInline(admin.TabularInline):
    model = ListingSlot
    extra = 1
    fields = ["start_date", "start_time", "end_date", "end_time"]


class ListingAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "user",
        "location_name",
        "rent_per_hour",
        "has_ev_charger",
        "parking_spot_size",
        "created_at",
        "rating_display",
    ]
    list_filter = ["parking_spot_size", "has_ev_charger", "charger_level", "created_at"]
    search_fields = ["title", "description", "location", "user__username"]
    readonly_fields = ["created_at", "updated_at", "avg_rating", "rating_count"]
    inlines = [ListingSlotInline]

    fieldsets = (
        ("Basic Information", {"fields": ("user", "title", "description", "location")}),
        ("Pricing", {"fields": ("rent_per_hour",)}),
        (
            "Parking Features",
            {
                "fields": (
                    "parking_spot_size",
                    "has_ev_charger",
                    "charger_level",
                    "connector_type",
                )
            },
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at", "avg_rating", "rating_count")},
        ),
    )

    def rating_display(self, obj):
        if obj.avg_rating:
            return f"{obj.avg_rating:.1f} ⭐ ({obj.rating_count})"
        return "No ratings"

    rating_display.short_description = "Rating"


admin.site.register(Listing, ListingAdmin)


class ListingSlotAdmin(admin.ModelAdmin):
    list_display = ["listing", "start_date", "start_time", "end_date", "end_time"]
    list_filter = ["start_date", "end_date"]
    search_fields = ["listing__title"]


admin.site.register(ListingSlot, ListingSlotAdmin)


class ReviewAdmin(admin.ModelAdmin):
    list_display = ["listing", "user", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["comment", "listing__title", "user__username"]
    readonly_fields = ["created_at"]


admin.site.register(Review, ReviewAdmin)
