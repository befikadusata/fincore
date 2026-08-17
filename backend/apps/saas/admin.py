from django.contrib import admin

from apps.saas.models import Plan, PlanFeature


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 1
    fields = ('name', 'codename', 'description')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """
    Operator surface for the subscription plan catalogue.

    Plans are platform-owned and global, so they deliberately have no
    tenant-facing write path: PlanViewSet is read-only and exposes only
    active plans. This admin is the sole place plans are created or
    repriced. Codenames drive FeatureGatingMiddleware, so editing one
    changes what subscribed tenants can reach.
    """
    list_display = ('name', 'slug', 'monthly_price', 'annual_price', 'currency', 'is_active')
    list_filter = ('is_active', 'currency')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PlanFeatureInline]
