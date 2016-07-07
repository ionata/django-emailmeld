from __future__ import unicode_literals
from operator import attrgetter
import re

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail.message import EmailMultiAlternatives
from django.db import models
from django.template.base import Template
from django.template.context import Context
try:
    from django.template.engine import Engine
except ImportError:
    Engine = None
    from django.template.loaders.eggs import Loader

from django.template import TemplateDoesNotExist
from django.utils.encoding import python_2_unicode_compatible, smart_text
from markdown import markdown


class EmailMeldBase(object):
    """Base class for creating emails.
        Minimum implementation = overriding, adding a 'template' attribute
        which points at a md/html/txt file template"""
    request_attrs = {}
    use_base_template = True
    use_database = True
    urls_resolved = False
    template = None
    template_tags = ['tz']

    def __init__(self, payload, request=None, force_update=False):
        self.payload = payload
        if 'site' not in self.payload:
            try:
                self.payload['site'] = Site.objects.get_current()
            except Site.DoesNotExist:
                self.payload['site'] = ""
        self.payload['STATIC_URL'] = settings.STATIC_URL
        self.payload['has_request_attrs'] = True if request is not None else False

        # get the timezone for wrapping this email template
        self.timezone = self.payload.get('emailmeld_timezone', getattr(settings, 'EMAILMELD_TIMEZONE', 'UTC'))

        if request:
            for key, attr in self.request_attrs.items():
                payload[key] = attrgetter(attr)(request)

        if self.template is None:
            raise NotImplementedError(
                "EmailMeldBase implementation requires a valid self.template "
                "property to a django template file path location")

        if not self.use_database:
            return

        if force_update or getattr(settings, 'EMAILMELD_FORCE_UPDATE', False):
            self.meld = self.create_or_update()

        try:
            self.meld = EmailMeldModel.objects.get(template=self.template)
        except EmailMeldModel.DoesNotExist:
            self.meld = self.create_or_update()

    def prepare_email(self, recipient_list, from_email=None):
        """From the recipient list, create an email"""
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
        """Return rendered HTML if the email is html or md"""
        if self.get_email_type() not in ['html', 'md']:
            return None

        # render content and fix urls/emails
        template = self.get_template()
        template = Template(template)
        template = template.render(Context(self.payload))
        if not self.urls_resolved:
            template = self.fix_urls(template)
        if self.get_email_type() == 'md':
            template = markdown(template)
        self.payload['site'] = Site.objects.get_current()

        if not self.use_base_template:
            return template

        base_template = (
            "{{% extends '{base_template}' %}}{{% block {block_name} %}}\n"
            "{template}\n"
            "{{% endblock %}}"
        ).format(
            base_template=settings.EMAILMELD_BASE_TEMPLATE,
            block_name="content",
            template=template,
        )

        base_template = Template(base_template)
        base_template = base_template.render(Context(self.payload))

        return base_template

    def render_text(self):
        """Return the text rendering if the filetype is md or txt"""
        if self.get_email_type() == 'html':
            return None

        template = Template(self.get_template())
        return template.render(Context(self.payload))

    def get_subject(self):
        """Return either the in-database subject, or the subject from the template"""
        if self.use_database:
            base_subject = self.meld.subject
        else:
            base_subject = self.partition_template_string(self.get_template_string())[0]
        subject = getattr(settings, 'EMAILMELD_SUBJECT_PREFIX', '') + base_subject
        template = Template(subject)
        return template.render(Context(self.payload))

    def get_template(self):
        """Return either the in-database template, or the on-disk one"""
        if self.use_database:
            template = self.meld.body
        else:
            template = self.partition_template_string(self.get_template_string())[1]

        # wrap the template in timezone aware tags
        template = u"{{% load {template_tags} %}}{{% timezone \"{timezone}\" %}}{body}{{% endtimezone %}}".format(
            template_tags=" ".join(self.template_tags),
            body=template,
            timezone=self.timezone,
        )

        return template

    def get_template_string(self):
        """Use the same logic as django uses for getting a compiled template
            to get the contents"""
        for loader in self.get_template_loaders():
            try:
                try:
                    template_string = loader.get_contents(self.template)
                except AttributeError:  # Pre-1.9 compatibility
                    template_string = loader.load_template_source(self.template)[0]
                return template_string
            except TemplateDoesNotExist:
                pass
        # Raise if none of the loaders could find it
        raise TemplateDoesNotExist(self.template)

    def get_template_loaders(self):
        """Some loaders have nested loaders that are what we actually use."""
        if Engine is None:
            loader = Loader()
            return getattr(loader, 'loaders', [loader])

        engine = Engine.get_default()
        loaders = []
        for loader in engine.template_loaders:
            loaders += getattr(loader, 'loaders', [loader])
        return loaders

    @staticmethod
    def partition_template_string(template_string):
        """Splits a template string into subject and body"""
        subject = template_string.split("\n")[0]
        if template_string.startswith(subject + "\n\n"):
            # clean up a empty line after subject
            body = template_string.partition(subject + "\n\n")[2]
        else:
            body = template_string.partition(subject + "\n")[2]
        return subject, body

    def get_email_type(self, initial=False):
        """Determine the filetype of the template from the extension.
            Cached in DB, use initial=True to bypass"""
        if self.use_database and not initial:
            return self.meld.email_type
        try:
            email_type = self.template.split('.')[-1]
        except ValueError:
            raise NotImplementedError(
                "EmailMeldBase implementation template file must end with a "
                "supported file extension, ie .html .txt .md")
        return email_type

    def create_or_update(self):
        """Create or update a meld with the template name that corresponds to
            the template attribute"""
        email_type = self.get_email_type(initial=True)
        template_source = self.get_template_string()
        subject, body = self.partition_template_string(template_source)

        meld = EmailMeldModel.objects.get_or_create(
            template=self.template,
        )[0]

        meld.email_type = email_type
        meld.subject = subject
        meld.body = body
        meld.save()

        return meld

    @staticmethod
    def fix_urls(text):
        """Add href / mailto to urls"""
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
            (?xm) # verbose identify URLs in text (and multiline)
            (.*?)( # begin group search
            [a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)* # front part of email
            @ # ...needs an at sign in the middle
            (?i) # case insensitive on
            (?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+ # case insensitive match first part of domain
            (?:abogado|academy|accountants|active|actor|adult|aero|agency|airforce|allfinanz|alsace|amsterdam|android|apartments|aquarelle|archi|army|arpa|asia|associates|attorney|auction|audio|autos|axa|band|bank|bar|barclaycard|barclays|bargains|bayern|beer|berlin|best|bid|bike|bingo|bio|biz|black|blackfriday|bloomberg|blue|bmw|bnpparibas|boats|boo|boutique|brussels|budapest|build|builders|business|buzz|bzh|cab|cal|camera|camp|cancerresearch|canon|capetown|capital|caravan|cards|care|career|careers|cartier|casa|cash|casino|cat|catering|cbn|center|ceo|cern|channel|chat|cheap|christmas|chrome|church|citic|city|claims|cleaning|click|clinic|clothing|club|coach|codes|coffee|college|cologne|com|community|company|computer|condos|construction|consulting|contractors|cooking|cool|coop|country|courses|credit|creditcard|cricket|crs|cruises|cuisinella|cymru|dabur|dad|dance|dating|day|dclk|deals|degree|delivery|democrat|dental|dentist|desi|design|dev|diamonds|diet|digital|direct|directory|discount|dnp|docs|domains|doosan|durban|dvag|eat|edu|education|email|emerck|energy|engineer|engineering|enterprises|equipment|esq|estate|eurovision|eus|events|everbank|exchange|expert|exposed|fail|fans|farm|fashion|feedback|finance|financial|firmdale|fish|fishing|fit|fitness|flights|florist|flowers|flsmidth|fly|foo|football|forsale|foundation|frl|frogans|fund|furniture|futbol|gal|gallery|garden|gbiz|gdn|gent|ggee|gift|gifts|gives|glass|gle|global|globo|gmail|gmo|gmx|goldpoint|goog|google|gop|gov|graphics|gratis|green|gripe|guide|guitars|guru|hamburg|hangout|haus|healthcare|help|here|hermes|hiphop|hiv|holdings|holiday|homes|horse|host|hosting|house|how|ibm|ifm|immo|immobilien|industries|info|ing|ink|institute|insure|int|international|investments|irish|iwc|jcb|jetzt|jobs|joburg|juegos|kaufen|kddi|kim|kitchen|kiwi|koeln|krd|kred|kyoto|lacaixa|land|lat|latrobe|lawyer|lds|lease|legal|lgbt|lidl|life|lighting|limited|limo|link|loans|london|lotte|lotto|ltda|luxe|luxury|madrid|maison|management|mango|market|marketing|marriott|media|meet|melbourne|meme|memorial|menu|miami|mil|mini|mobi|moda|moe|monash|money|mormon|mortgage|moscow|motorcycles|mov|museum|nagoya|name|navy|net|network|neustar|new|nexus|ngo|nhk|nico|ninja|nra|nrw|ntt|nyc|okinawa|one|ong|onl|ooo|org|organic|osaka|otsuka|ovh|paris|partners|parts|party|pharmacy|photo|photography|photos|physio|pics|pictures|pink|pizza|place|plumbing|pohl|poker|porn|post|praxi|press|pro|prod|productions|prof|properties|property|pub|qpon|quebec|realtor|recipes|red|rehab|reise|reisen|reit|ren|rentals|repair|report|republican|rest|restaurant|reviews|rich|rio|rip|rocks|rodeo|rsvp|ruhr|ryukyu|saarland|sale|samsung|sarl|saxo|sca|scb|schmidt|school|schule|schwarz|science|scot|services|sew|sexy|shiksha|shoes|shriram|singles|sky|social|software|sohu|solar|solutions|soy|space|spiegel|study|style|sucks|supplies|supply|support|surf|surgery|suzuki|sydney|systems|taipei|tatar|tattoo|tax|technology|tel|temasek|tennis|tienda|tips|tires|tirol|today|tokyo|tools|top|toshiba|town|toys|trade|training|travel|trust|tui|university|uno|uol|vacations|vegas|ventures|versicherung|vet|viajes|video|villas|vision|vlaanderen|vodka|vote|voting|voto|voyage|wales|wang|watch|webcam|website|wed|wedding|whoswho|wien|wiki|williamhill|wme|work|works|world|wtc|wtf|xxx|xyz|yachts|yandex|yodobashi|yoga|yokohama|youtube|zip|zone|zuerich|[A-Z]{2}) # match top level
            (i?) # case insensitive off
            ) # end group search
            ''')

        for url in set([x[0] for x in re.findall(pat_url, text)]):
            text = text.replace(url, '<a href="%(url)s">%(url)s</a>' % {"url": url})

        for email in set([x[1] for x in re.findall(pat_email, text)]):
            text = text.replace(email, '<a href="mailto:%(email)s">%(email)s</a>' % {"email": email})

        return text


@python_2_unicode_compatible
class EmailMeldModel(models.Model):
    """The actual in-database format"""
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

    def __str__(self):
        return smart_text(self.subject)
