from django.contrib import admin
from mail.models import LicenceData, Mail, MailboxConfig, MailReadStatus, UsageUpdate


class LicenceDataAdmin(admin.ModelAdmin):
    def status(self, obj):
        return obj.mail.status

    list_display = ["pk", "licence_ids", "source", "status"]


class MailAdmin(admin.ModelAdmin):
    list_display = ["pk", "edi_filename", "status", "extract_type", "sent_at", "response_date"]


admin.site.register(MailboxConfig)
admin.site.register(MailReadStatus)
admin.site.register(UsageUpdate)
admin.site.register(LicenceData, LicenceDataAdmin)
admin.site.register(Mail, MailAdmin)
