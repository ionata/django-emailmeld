from emailmeld.models import EmailMeldBase
from django.http import Http404, HttpResponse
from django.template.base import Template
from django.template.context import Context


class EmailTextTest(EmailMeldBase):
    template = "emailmeld.txt"


class EmailHtmlTest(EmailMeldBase):
    template = "emailmeld.html"


class EmailHtmlWithBaseTest(EmailMeldBase):
    template = "emailmeld_with_base.html"


class EmailMarkdownTest(EmailMeldBase):
    template = "emailmeld.md"


def tester(request):

    payload = {'first_name': 'thomas'}
    to = ['thomas@ionata.com.au']

    #email1 = EmailTextTest(payload)
    #email1.send(to)

    #email2 = EmailHtmlTest(payload)
    #email2.send(to)

    #email3 = EmailMarkdownTest(payload)
    #email3.send(to)

    email4 = EmailHtmlWithBaseTest(payload, force_update=True)
    email4.send(to)

    return HttpResponse(Template('{% load debug_tags %}<pre>{{ request.path}}{{ request.META|dir}}</pre>').render(Context({'request': request})))
