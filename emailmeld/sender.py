from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def send_mail_task(subject, message, from_email, recipient_list):
    message = EmailMessage("Discover Special Value - {0}".format(subject), message, from_email, recipient_list)
    message.send()


def send_html_mail_task(subject, text_message, html_message, from_email, recipient_list, template='email/email_base.html'):
    if template is not None:
        html_message = render_to_string(template, {'content': mark_safe(html_message)})  # render html into an email template

    message = EmailMultiAlternatives("Discover Special Value - {0}".format(subject), html_message, from_email, recipient_list)
    message.content_subtype = "html"
    message.attach_alternative(text_message, "text/plain")
    message.send()
