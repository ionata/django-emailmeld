from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail.message import EmailMultiAlternatives
from django.db import models
from django.template.base import Template
from django.template.context import Context
from django.template.loaders.eggs import Loader
from django.utils.encoding import smart_unicode
from markdown import markdown
from operator import attrgetter
import re


class EmailMeldBase(object):

    request_attrs = {
    }
    use_base_template = True

    def __init__(self, payload, request=None, force_update=False):
        self.payload = payload
        try:
            self.payload['site'] = Site.objects.get_current()
        except Site.DoesNotExist:
            self.payload['site'] = ""
        self.payload['STATIC_URL'] = settings.STATIC_URL
        self.payload['has_request_attrs'] = True if request is not None else False

        if request:
            for key, attr in self.request_attrs.items():
                payload[key] = attrgetter(attr)(request)

        if not hasattr(self, 'template'):
            raise NotImplementedError("EmailMeldBase implementation requires a valid self.template property to a django template file path location")

        if force_update or getattr(settings, 'EMAILMELD_FORCE_UPDATE', False):
            self.meld = self.create_or_update()

        try:
            self.meld = EmailMeldModel.objects.get(template=self.template)
        except EmailMeldModel.DoesNotExist:
            self.meld = self.create_or_update()

    def prepare_email(self, recipient_list, from_email=None):
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        subject = self.get_subject()

        html_message = self.render_html()
        text_message = self.render_text()

        if text_message is not None:
            message = EmailMultiAlternatives(subject, text_message, from_email, recipient_list)
            if html_message is not None:
                message.attach_alternative(html_message, "text/html")
        else:
            message = EmailMultiAlternatives(subject, html_message, from_email, recipient_list)
            message.content_subtype = "html"

        return message

    def send(self, recipient_list, from_email=None):
        message = self.prepare_email(recipient_list, from_email)
        return message.send()

    def render_html(self):
        if self.meld.email_type not in ['html', 'md']:
            return None

        # render content and fix urls/emails
        t = self.get_template()
        t = Template(t)
        t = t.render(Context(self.payload))
        t = self.fix_urls(t)
        if self.meld.email_type == 'md':
            t = markdown(t)
        self.payload['site'] = Site.objects.get_current()

        if not self.use_base_template:
            return t

        b = "{{% extends '{base_template}' %}}{{% block {block_name} %}}\n{template}\n{{% endblock %}}".format(
            base_template=settings.EMAILMELD_BASE_TEMPLATE,
            block_name="content",
            template=t,
        )

        b = Template(b)
        b = b.render(Context(self.payload))

        return b

    def render_text(self):
        if self.meld.email_type == 'html':
            return None

        t = Template(self.get_template())
        return t.render(Context(self.payload))

    def get_subject(self):
        subject = getattr(settings, 'EMAILMELD_SUBJECT_PREFIX', '') + self.meld.subject
        t = Template(subject)
        return t.render(Context(self.payload))

    def get_template(self):
        return self.meld.body

    def create_or_update(self):
        try:
            email_type = self.template.split('.')[-1]
        except ValueError:
            raise NotImplementedError("EmailMeldBase implementation template file must end with a supported file extension, ie .html .txt .md")

        template_source = Loader().load_template_source(self.template)[0]
        subject = template_source.split("\n")[0]

        if template_source.startswith(subject + "\n\n"):
            # clean up a empty line after subject
            body = template_source.partition(subject + "\n\n")[2]
        else:
            body = template_source.partition(subject + "\n")[2]

        meld = EmailMeldModel.objects.get_or_create(
            template=self.template,
        )[0]

        meld.email_type = email_type
        meld.subject = subject
        meld.body = body
        meld.save()

        return meld

    def fix_urls(self, text):
        pat_url = re.compile(r'''
                         (?x)( # verbose identify URLs within text
             (http|https|ftp|gopher) # make sure we find a resource type
                           :// # ...needs to be followed by colon-slash-slash
                (\w+[:.]?){2,} # at least two domain groups, e.g. (gnosis.)(cx)
                          (/?| # could be just the domain name (maybe w/ slash)
                    [^ \n\r"]+ # or stuff then space, newline, tab, quote
                        [\w/]) # resource name ends in alphanumeric or slash
             (?=[\s\.,>)'"\]]) # assert: followed by white or clause ending
                             ) # end of match group
                               ''')
        pat_email = re.compile(r'''
                        (?xm)  # verbose identify URLs in text (and multiline)
                     (?=^.{11} # Mail header matcher
             (?<!Message-ID:|  # rule out Message-ID's as best possible
                 In-Reply-To)) # ...and also In-Reply-To
                        (.*?)( # must grab to email to allow prior lookbehind
            ([A-Za-z0-9-]+\.)? # maybe an initial part: DAVID.mertz@gnosis.cx
                 [A-Za-z0-9-]+ # definitely some local user: MERTZ@gnosis.cx
                             @ # ...needs an at sign in the middle
                  (\w+\.?){2,} # at least two domain groups, e.g. (gnosis.)(cx)
             (?=[\s\.,>)'"\]]) # assert: followed by white or clause ending
                             ) # end of match group
                               ''')

        for url in re.findall(pat_url, text):
            text = text.replace(url[0], '<a href="%(url)s">%(url)s</a>' % {"url": url[0]})

        for email in re.findall(pat_email, text):
            text = text.replace(email[1], '<a href="mailto:%(email)s">%(email)s</a>' % {"email": email[1]})

        return text


class EmailMeldModel(models.Model):

    # maps to template file extension
    EMAIL_TYPE_CHOICES = (
        ("txt", "Text"),
        ("html", "HTML"),
        ("md", "Markdown"),
    )

    email_type = models.CharField(max_length=10, choices=EMAIL_TYPE_CHOICES, default="MARKDOWN")
    template = models.CharField(max_length=255, unique=True)

    subject = models.CharField(max_length=255)
    body = models.TextField()

    def  __unicode__(self):
        return smart_unicode(self.subject)
