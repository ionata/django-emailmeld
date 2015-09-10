"""Example celery tasks for email dispatch"""
import importlib

from celery.app import shared_task
from django.utils.translation import ugettext_lazy as _


def get_class(class_path_string):
    """Provide an absolute dotted path to a class, get that class"""
    module, klass = class_path_string.rsplit('.', 1)
    module = importlib.import_module(module)
    email_class = getattr(module, klass, None)
    if email_class is None:
        raise ImportError(_("Tried to use an invalid class for emailing"))
    return email_class


@shared_task
def send_emailmeld_task(email_class_str, payload, to):
    """ email_class_str is the full dotted path to the class to use
        By not using a class, we avoid needing to pickle
        payload is a context for using within the email class
        to is either an email address, or a list of email addresses
    """
    email_class = get_class(email_class_str)
    email = email_class(payload)
    if not isinstance(to, list):
        to = [to]
    email.send(to)


def send_email(email_class_str, payload, to):
    """Shortcut for sending an emailmeld email through celery"""
    get_class(email_class_str)  # Try it before queueing, so we know it won't explode
    send_emailmeld_task.apply_async([email_class_str, payload, to])


@shared_task
def send_emailmeld_tasks(email_class_str, payload_list):
    """ email_class_str is the full dotted path to the class to use
        By not using a class, we avoid needing to pickle
        Payload_list is a list of contexts for using within the email class
        Because each payload may be for a different individual, 'to' is set as
        an email or a list of emails within the context.
    """
    for payload in payload_list:
        send_emailmeld_task(email_class_str, payload, payload['to'])


def send_emails(email_class_str, payload_list, when=None):
    """Shortcut for sending multiple emailmeld emails through celery
        To delay the sending, provide a datetime
    """
    get_class(email_class_str)  # Try it before queueing, so we know it won't explode
    if when is None:
        send_emailmeld_tasks.apply_async([email_class_str, payload_list])
    else:
        send_emailmeld_tasks.apply_async([email_class_str, payload_list], eta=when)
