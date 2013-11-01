__all__ = [
    "Emailer",
]
import re
import os
import smtplib
import string
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
import getpass
from socket import gaierror, getfqdn

from nparcel.utils.log import log


class Emailer(object):
    """Nparcel emailer.

    .. attribute:: template_base
        directory where templates are read from

    """
    _template_base = os.path.join(os.path.expanduser('~'),
                                  '.nparceld',
                                  'templates')

    def __init__(self,
                 sender=None,
                 recipients=None):
        """Nparcel emailer initialiser.

        """
        self._sender = sender
        if self._sender is None:
            self._sender = "%s@%s" % (getpass.getuser(), getfqdn())

        if recipients is None:
            self._recipients = []
        else:
            self._recipients = recipients

    @property
    def sender(self):
        return self._sender

    def set_sender(self, value):
        self._sender = value

    @property
    def recipients(self):
        return self._recipients

    def set_recipients(self, values):
        del self._recipients[:]

        if values is not None:
            self._recipients.extend(values)

    @property
    def template_base(self):
        return self._template_base

    def set_template_base(self, value):
        self._template_base = value

    def send(self, subject=None, msg=None, mime_message=None, dry=False):
        """Send the *msg*.

        Performs a simple validation check of the recipients and will
        only send the email if all are OK.

        Empty recipient lists are ignored and no email send attempt is made.

        **Args:**
            subject: the email subject

            msg: email message

        **Kwargs:**
            dry: do not send, only report what would happen

        """
        log.info('Sending email comms ...')
        status = True

        # Verify email addresses.
        if not len(self.recipients):
            log.warn('No email recipients provided')
            status = False

        if status:
            for recipient in self.recipients:
                if not self.validate(recipient):
                    status = False
                    break

        if status:
            # OK, send the message.
            content = mime_message
            if content is None:
                mime_msg = MIMEText(msg)
                mime_msg['Subject'] = subject
                mime_msg['From'] = self.sender
                mime_msg['To'] = ", ".join(self.recipients)
                content = mime_msg.as_string()

            # ... and send.
            log.info('Sending email to recipients: "%s"' %
                      str(self.recipients))
            s = None
            if not dry:
                try:
                    s = smtplib.SMTP()
                except gaierror, err:
                    status = False
                    log.error('Could not connect to SMTP server "%s"' % err)

            if s is not None:
                s.connect()
                try:
                    s.sendmail(self.sender,
                               self.recipients,
                               content)
                except (smtplib.SMTPRecipientsRefused,
                        smtplib.SMTPHeloError,
                        smtplib.SMTPSenderRefused,
                        smtplib.SMTPDataError), err:
                    status = False
                    log.warn('Could not send email: %s' % err)
                s.close()

        return status

    def validate(self, email):
        """Validate the *email* address.

        Runs a simple regex validation across the *email* address is

        **Args:**
            email: the email address to validate

        **Returns:**
            boolean ``True`` if the email validates

            boolean ``False`` if the email does not validate

        """
        status = True

        err = 'Email "%s" validation failed' % email
        r = re.compile("^[a-zA-Z0-9._%-+]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$")
        m = r.match(email)
        if m is None:
            status = False
            log.error(err)

        return status

    def create_comms(self,
                     subject,
                     data,
                     template=None,
                     err=False):
        """Create the MIME multipart message.

        **Args:**
            subject: the email subject

            data: dictionary structure of items to expected by the HTML
            email templates::

                {'name': 'Auburn Newsagency',
                 'address': '119 Auburn Road',
                 'suburb': 'HAWTHORN EAST',
                 'postcode': '3123',
                 'barcode': '218501217863-barcode',
                 'item_nbr': '3456789012-item_nbr'}

        **Kwargs:**
            base_dir: override the standard location to search for the
            templates (default ``~user_home/.nparceld/templates``).

        **Returns:**
            MIME multipart-formatted serialised string

        """
        mime_msg = MIMEMultipart('related')
        mime_msg['Subject'] = subject
        mime_msg['From'] = self.sender
        mime_msg['To'] = ", ".join(self.recipients)

        msgAlternative = MIMEMultipart('alternative')
        mime_msg.attach(msgAlternative)

        body_html = 'email_%s_html.t' % template
        if err:
            body_html = 'email_err_%s_html.t' % template

        html_template = os.path.join(self.template_base, body_html)
        log.debug('Email body template: "%s"' % html_template)
        f = open(html_template)
        body_t = f.read()
        f.close()
        body_s = string.Template(body_t)
        body = body_s.substitute(**data)

        f = open(os.path.join(self.template_base, 'email_html.t'))
        main_t = f.read()
        f.close()
        main_s = string.Template(main_t)
        main = main_s.substitute(body=body)

        main_text = MIMEText(main, 'html')
        msgAlternative.attach(main_text)

        return mime_msg.as_string()

    def get_subject_line(self,
                         data,
                         template='body'):
        """Construct email subject line from a template.

        **Args**:
            *data*: dictionary structure that features the tokens that feed
            into the template

            *template*: template file that contains the subject line
            construct

        **Returns**:
            string representation of the subject

        """
        subject_html = 'subject_%s_html.t' % template

        subject_template = os.path.join(self.template_base, subject_html)
        log.debug('Email subject template: "%s"' % subject_template)
        subject_string = str()
        try:
            f = open(subject_template)
            subject_t = f.read()
            f.close()
            subject_s = string.Template(subject_t)
            subject_string = subject_s.substitute(**data)
        except IOError, e:
            log.error('Unable to find subject template %s: %s' %
                      (subject_template, e))

        subject_string = subject_string.rstrip()
        log.debug('Email comms subject string: "%s"' % subject_string)

        return subject_string
