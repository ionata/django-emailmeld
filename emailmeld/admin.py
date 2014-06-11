from django.contrib import admin
from emailmeld.models import EmailMeldModel


class EmailMeldModelAdmin(admin.ModelAdmin):
    pass

admin.site.register(EmailMeldModel, EmailMeldModelAdmin)
