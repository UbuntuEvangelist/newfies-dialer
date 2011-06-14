from django.contrib import admin
#from django.utils.translation import ugettext as _
from voip_app.models import VoipApp


class VoipAppAdmin(admin.ModelAdmin):
    """Allows the administrator to view and modify certain attributes
    of a VoipApp."""
    list_display = ('id', 'name', 'description', 'type', 'created_date')
    list_display_links = ('name', )
    list_filter = ['created_date', ]
    ordering = ('id', )
admin.site.register(VoipApp, VoipAppAdmin)
