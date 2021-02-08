from django.contrib import admin
from mail.models import LicenceData, LicenceUpdate, Mail, MailboxConfig, MailReadStatus, UsageUpdate

admin.site.register(MailboxConfig)
admin.site.register(MailReadStatus)
admin.site.register(UsageUpdate)
admin.site.register(LicenceData)
admin.site.register(LicenceUpdate)
admin.site.register(Mail)
