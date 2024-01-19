from django.contrib import admin

from mail.models import LicenceData, LicencePayload, Mail


class LicencePayloadInline(admin.TabularInline):
    model = LicenceData.licence_payloads.through
    raw_id_fields = ("licencepayload",)
    verbose_name = "LicencePayload"
    verbose_name_plural = "Licence Payloads linked to this LicenceData record"
    extra = 0
    can_delete = False


class LicenceDataAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.select_related("mail")

    def mail_status(self, obj):
        return obj.mail.status

    list_display = ["pk", "licence_ids", "source", "mail_status"]
    exclude = ["licence_payloads"]
    inlines = [LicencePayloadInline]


class MailAdmin(admin.ModelAdmin):
    list_display = ["pk", "edi_filename", "status", "extract_type", "sent_at", "response_date"]

    def has_change_permission(self, request, obj=None):
        """Prevent modification of Mail records to minimise the risk of introducing data bugs.

        When django saves records an extra \r is being added to the textarea fields on each line.
        This makes columns like response_data invalid and we are not able to process the chief data.
        """
        return False


admin.site.register(LicenceData, LicenceDataAdmin)
admin.site.register(Mail, MailAdmin)
admin.site.register(LicencePayload)
