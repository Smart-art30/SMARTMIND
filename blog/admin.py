
from django.contrib import admin
from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import (
    Post,
    Category,
    Tag,
    AttachmentPurchase,
    PaystackTransaction,
    CreatorWallet,
    CreatorSale,
    WalletLedgerEntry,
    CreatorPayout,
)


class PostAdminForm(forms.ModelForm):
    content = forms.CharField(
        widget=CKEditor5Widget(config_name="default")
    )

    class Meta:
        model = Post
        fields = "__all__"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm

    list_display = (
        "title",
        "category",
        "author",
        "school",
        "status",
        "approved",
        "created_at",
    )

    list_filter = (
        "status",
        "approved",
        "category",
        "school",
    )

    search_fields = ("title", "content")

    filter_horizontal = (
        "tags",
        "target_classes",
        "likes",
    )

    prepopulated_fields = {
        "slug": ("title",)
    }


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(AttachmentPurchase)
class AttachmentPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "post",
        "amount_paid",
        "currency",
        "created_at",
    )

    list_filter = ("currency", "created_at")

    search_fields = (
        "user__username",
        "post__title",
        "payment_reference",
    )

    readonly_fields = ("created_at",)


# ==========================================================
# READ-ONLY FINANCIAL RECORDS
# ==========================================================

class ReadOnlyFinancialAdmin(admin.ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        return [
            field.name
            for field in self.model._meta.fields
        ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ==========================================================
# PAYSTACK TRANSACTIONS
# ==========================================================

@admin.register(PaystackTransaction)
class PaystackTransactionAdmin(ReadOnlyFinancialAdmin):

    list_display = (
        "reference",
        "user",
        "post",
        "amount",
        "currency",
        "status",
        "paid_at",
        "created_at",
    )

    list_filter = (
        "status",
        "currency",
        "created_at",
    )

    search_fields = (
        "reference",
        "email",
        "user__username",
        "post__title",
        "gateway_transaction_id",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"


# ==========================================================
# CREATOR WALLETS
# ==========================================================

@admin.register(CreatorWallet)
class CreatorWalletAdmin(ReadOnlyFinancialAdmin):

    list_display = (
        "creator",
        "available_balance",
        "total_earned",
        "total_paid",
        "currency",
        "updated_at",
    )

    search_fields = (
        "creator__username",
        "creator__email",
    )

    list_filter = ("currency",)
    ordering = ("-updated_at",)


# ==========================================================
# CREATOR SALES
# ==========================================================

@admin.register(CreatorSale)
class CreatorSaleAdmin(ReadOnlyFinancialAdmin):

    list_display = (
        "post",
        "creator",
        "gross_amount",
        "platform_commission",
        "creator_earning",
        "commission_rate",
        "mpesa_transaction",
        "paystack_transaction",
        "created_at",
    )

    list_filter = (
        "commission_rate",
        "created_at",
    )

    search_fields = (
        "creator__username",
        "post__title",
        "paystack_transaction__reference",
        "mpesa_transaction__checkout_request_id",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"


# ==========================================================
# WALLET LEDGER
# ==========================================================

@admin.register(WalletLedgerEntry)
class WalletLedgerEntryAdmin(ReadOnlyFinancialAdmin):

    list_display = (
        "wallet",
        "entry_type",
        "amount",
        "sale",
        "payout",
        "description",
        "created_at",
    )

    list_filter = (
        "entry_type",
        "created_at",
    )

    search_fields = (
        "wallet__creator__username",
        "description",
        "sale__post__title",
        "payout__mpesa_reference",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"


# ==========================================================
# CREATOR PAYOUTS
# ==========================================================

@admin.register(CreatorPayout)
class CreatorPayoutAdmin(ReadOnlyFinancialAdmin):

    list_display = (
        "creator",
        "amount",
        "phone_number",
        "status",
        "mpesa_reference",
        "requested_at",
        "processed_at",
    )

    list_filter = (
        "status",
        "requested_at",
    )

    search_fields = (
        "creator__username",
        "phone_number",
        "mpesa_reference",
    )

    ordering = ("-requested_at",)
