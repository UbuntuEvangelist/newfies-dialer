from django.contrib import admin
from django.contrib import messages
from django.conf.urls.defaults import *
from django.utils.translation import ugettext as _
from django.db.models import *
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from dialer_campaign.models import *
from dialer_campaign.forms import *
from dialer_campaign.function_def import *
from dialer_campaign.views import common_send_notification
import csv


class CampaignAdmin(admin.ModelAdmin):
    """Allows the administrator to view and modify certain attributes
    of a Campaign."""
    fieldsets = (
        ('Standard options', {
            'fields': ('name', 'description', 'user', 'status', 'startingdate',
                       'expirationdate', 'aleg_gateway', 'voipapp',
                       'extra_data', 'phonebook'),
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('frequency', 'callmaxduration', 'maxretry',
                       'intervalretry', 'calltimeout', 'daily_start_time',
                       'daily_stop_time', 'monday', 'tuesday', 'wednesday',
                       'thursday', 'friday', 'saturday', 'sunday')
        }),
    )
    list_display = ('id', 'name', 'user', 'startingdate',
                    'expirationdate', 'frequency', 'callmaxduration',
                    'maxretry', 'aleg_gateway',#'intervalretry', 'calltimeout',
                    'voipapp', 'extra_data', 'status',
                    'update_campaign_status', 'count_contact_of_phonebook',
                    'campaignsubscriber_detail', 'progress_bar')

    list_display_links = ('name', )
    #list_filter = ['user', 'status', 'startingdate', 'created_date']
    ordering = ('id', )
    filter_horizontal = ('phonebook',)

    def get_urls(self):
        urls = super(CampaignAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^$', self.admin_site.admin_view(self.changelist_view)),
            (r'^add/$', self.admin_site.admin_view(self.add_view)),
        )
        return my_urls + urls

    def add_view(self, request, extra_context=None):
        """Override django add_view method for checking dialer setting limit

        **Logic Description**:

            * Before adding campaign, checked dialer setting limit if user is
              linked with it & if it is matched, user will be redirected to
              campaign list
        """
        # Check dialer setting limit
        # check Max Number of running campaign
        if check_dialer_setting(request, check_for="campaign"):
            msg = _("you have too many campaign. Max allowed\
            %s" % dialer_setting_limit(request, limit_for="campaign"))
            messages.error(request, msg)

            # campaign limit reached
            common_send_notification(request, '3')
            return HttpResponseRedirect(reverse(
                        "admin:dialer_campaign_campaign_changelist"))
        ctx = {}
        return super(CampaignAdmin, self).add_view(request, extra_context=ctx)
admin.site.register(Campaign, CampaignAdmin)


class PhonebookAdmin(admin.ModelAdmin):
    """Allows the administrator to view and modify certain attributes
    of a Phonebook."""
    list_display = ('id', 'name', 'description', 'user', 'created_date',
                    'phonebook_contacts')
    list_filter = ['user', 'created_date']
    ordering = ('id', )
admin.site.register(Phonebook, PhonebookAdmin)


class ContactAdmin(admin.ModelAdmin):
    """Allows the administrator to view and modify certain attributes
    of a Contact."""
    list_display = ('id', 'phonebook', 'contact', 'contact_name', 'email',
                    'country', 'city', 'status', 'created_date')
    list_filter = ['phonebook', 'created_date']
    ordering = ('id', )

    def get_urls(self):
        urls = super(ContactAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^add/$', self.admin_site.admin_view(self.add_view)),
            (r'^import_contact/$',
             self.admin_site.admin_view(self.import_contact)),
        )
        return my_urls + urls

    def add_view(self, request, extra_context=None):
        """Override django admin add_view method for checking dialer setting
        limit

        **Logic Description**:

            * Before adding contact, checked dialer setting limit if user is
              linked with it & if it is matched, user will be redirected to
              contact list
        """
        # Check dialer setting limit
        if request.user and request.method == 'POST':
            # check Max Number of subscriber per campaign
            if check_dialer_setting(request, check_for="contact"):
                msg = _("You have too many contacts per campaign.\
                You are allowed a maximum of %s" \
                % dialer_setting_limit(request, limit_for="contact"))
                messages.error(request, msg)

                # campaign limit reached
                common_send_notification(request, '3')
                return HttpResponseRedirect(reverse(
                            "admin:dialer_campaign_contact_changelist"))

        ctx = {}
        return super(ContactAdmin, self).add_view(request, extra_context=ctx)

    def import_contact(self, request):
        """Added custom method in django admin view to import CSV file of
        Contact

        **Attributes**:

            * ``form`` - Contact_fileImport
            * ``template`` - admin/dialer_campaign/contact/import_contact.html

        **Logic Description**:

            * Before adding contact, checked dialer setting limit if user is
              linked with it
            * Add new contact which will belong to logged in user
              via csv file & get the result (how many recrods are uploaded
              successfully & which are not)

        **Important variable**:

            * total_rows - Total no. of records of CSV file
            * retail_record_count - No. of records which are imported from
              CSV file
        """
        # Check dialer setting limit
        if request.user and request.method == 'POST':
            # check Max Number of subscriber per campaign
            if check_dialer_setting(request, check_for="contact"):
                msg = _("You have too many contacts per campaign.\
                You are allowed a maximum of %s" \
                % dialer_setting_limit(request, limit_for="contact"))
                messages.error(request, msg)

                # campaign limit reached
                common_send_notification(request, '3')
                return HttpResponseRedirect(reverse(
                            "admin:dialer_campaign_contact_changelist"))

        opts = Contact._meta
        app_label = opts.app_label
        file_exts = ('.csv', )
        rdr = ''  # will contain CSV data
        msg = ''
        success_import_list = []
        error_import_list = []
        type_error_import_list = []
        if request.method == 'POST':
            form = Contact_fileImport(request.user, request.POST,
                                      request.FILES)
            if form.is_valid():
                # col_no - field name
                #  0     - contact
                #  1     - last_name
                #  2     - first_name
                #  3     - email
                #  4     - description
                #  5     - status
                #  6     - additional_vars
                # To count total rows of CSV file
                records = csv.reader(request.FILES['csv_file'],
                                 delimiter=',', quotechar='"')
                total_rows = len(list(records))

                rdr = csv.reader(request.FILES['csv_file'],
                                 delimiter=',', quotechar='"')
                contact_record_count = 0
                # Read each Row
                for row in rdr:
                    if (row and str(row[0]) > 0):
                        row = striplist(row)
                        try:
                            # check field type
                            int(row[5])

                            phonebook = \
                            Phonebook.objects.get(pk=request.POST['phonebook'])
                            try:
                                # check if prefix is alredy
                                # exist with retail plan or not
                                contact = Contact.objects.get(
                                     phonebook_id=phonebook.id,
                                     contact=row[0])
                                msg = _('Contact is already exist !!')
                                error_import_list.append(row)
                            except:
                                # if not, insert record
                                Contact.objects.create(
                                      phonebook=phonebook,
                                      contact=row[0],
                                      last_name=row[1],
                                      first_name=row[2],
                                      email=row[3],
                                      description=row[4],
                                      status=int(row[5]),
                                      additional_vars=row[6])
                                contact_record_count = \
                                    contact_record_count + 1
                                msg = \
                                '%d Contact(s) are uploaded  \
                                 successfully out of %d row(s) !!'\
                                 % (contact_record_count, total_rows)
                                success_import_list.append(row)
                        except:
                            msg = _("Error : invalid value for import! \
                                   Please look at the import samples.")
                            type_error_import_list.append(row)
        else:
            form = Contact_fileImport(request.user)

        ctx = RequestContext(request, {
        'title': _('Import Contact'),
        'form': form,
        'opts': opts,
        'model_name': opts.object_name.lower(),
        'app_label': _('Dialer_campaign'),
        'rdr': rdr,
        'msg': msg,
        'success_import_list': success_import_list,
        'error_import_list': error_import_list,
        'type_error_import_list': type_error_import_list,
        })
        return render_to_response(
               'admin/dialer_campaign/contact/import_contact.html',
               context_instance=ctx)
admin.site.register(Contact, ContactAdmin)


class CampaignSubscriberAdmin(admin.ModelAdmin):
    """Allows the administrator to view and modify certain attributes
    of a CampaignSubscriber."""
    list_display = ('id', 'contact', 'campaign', 'callrequest',
                    'last_attempt', 'count_attempt', 'duplicate_contact',
                    'contact_name', 'status', 'created_date')
    list_filter = ['campaign', 'created_date', 'last_attempt']
    ordering = ('id', )
admin.site.register(CampaignSubscriber, CampaignSubscriberAdmin)
