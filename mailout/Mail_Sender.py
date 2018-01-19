from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
import argparse
import csv
import os
import sys
import smtplib
import time

class Mail_Sender:

    def __init__(self, config, db, generator, print_only=False,
                 debug=False, limit=None, test_to=None, ccs=[], bccs=[]):
        self.db = db
        self.generator = generator
        self.config = config
        self.from_addr = config.get('Envelope', 'from')
        self.sender = config.get('Envelope', 'sender')
        self.reply_to = config.get('Envelope', 'reply-to')
        self.ccs = ccs if len(ccs) > 0 \
                   else  [ self._get_optional('Envelope', 'cc', dflt="") ]
        self.bccs = bccs if len(bccs) > 0 \
                   else  [ self._get_optional('Envelope', 'bcc', dflt="") ]
        self.auth_user = self._get_optional('SMTP', 'auth-user')
        self.auth_passwd = self._get_optional('SMTP', 'auth-password')
        self.smtp_server = config.get('SMTP', 'server')
        self.start_tls = config.getboolean('SMTP', 'start-tls')
        if self.auth_user is not None and not self.start_tls:
            raise Exception("Insecure!  Don't specify an auth-user without start-tls")
        self.hide_recipients = config.getboolean('Envelope', 'hide-recipients')
        self.print_only = print_only
        self.debug = debug
        self.test_to = test_to
        self.smtp = None
        self.msg_tries = 0
        self.all_msgs_sent = 0
        self.all_copies_sent = 0
        self.max_tries = config.getint('SMTP', 'max-tries-per-connection')
        self.rate = config.getfloat('SMTP', 'max-messages-per-second')
        self.limit = limit
        self.delay_after_send = 1.0 / self.rate if self.rate else None
        self.encoding = config.get('Body', 'encoding')
        self.plain_only = config.getboolean('Body', 'plain-only')
        self.html_only = config.getboolean('Body', 'html-only')
        self.hide_recipients = config.getboolean('Envelope', 'hide-recipients')
        if debug:
            sys.stderr.write('Mail_Sender: %s\n' % self.__dict__)

    def _get_optional(self, section, option, dflt=None):
        if self.config.has_option(section, option):
            res = self.config.get(section, option)
            return dflt if res is None else res
        else:
            return dflt

    @staticmethod
    def init_config(config):
        config.add_section('SMTP')
        config.set('SMTP', 'server', '127.0.0.1')
        config.set('SMTP', 'max-tries-per-connection', 100)
        config.set('SMTP', 'max-messages-per-second', 1.0)
        config.set('SMTP', 'auth-user', None)
        config.set('SMTP', 'auth-password', None)
        config.set('SMTP', 'start-tls', True)
        config.add_section('Envelope')
        config.set('Envelope', 'from',
                   'NeCTAR Research Cloud <bounces@rc.nectar.org.au>')
        config.set('Envelope', 'sender', None)
        config.set('Envelope', 'cc', None)
        config.set('Envelope', 'bcc', None)
        config.set('Envelope', 'reply-to', 'support@rc.nectar.org.au')
        config.set('Envelope', 'subject', None)
        config.set('Envelope', 'hide-recipients', False)
        config.add_section('Body')
        config.set('Body', 'encoding', 'ASCII')
        config.set('Body', 'html-only', False)
        config.set('Body', 'plain-only', False)

    def send_email(self, recipients, subject, text, html=None):
        if self.limit != None and self.all_msgs_sent >= self.limit:
            raise Exception('Stopping: %s messages processed / sent' %
                            self.all_msgs_sent)

        if self.html_only and html is None:
            raise Exception('The mailout config has "html-only" selected ' +
                            'but the email body generator did not find ' +
                            'an HTML template')
        
        msg = MIMEMultipart('alternative')
        if not self.html_only:
            msg.attach(MIMEText(text, 'plain', self.encoding))
        if not self.plain_only and html is not None:
            msg.attach(MIMEText(html, 'html', self.encoding))
            
        msg['From'] = self.from_addr
        msg['Reply-to'] = self.reply_to
        if not self.hide_recipients:
            msg['To'] = "; ".join(recipients)
        if self.sender:
            msg['Sender'] = self.sender
        if len(self.ccs) > 0:
            msg['Cc'] = "; ".join(self.ccs)
        if len(self.bccs) > 0:
            msg['Bcc'] = "; ".join(self.bccs)
        msg['Subject'] = subject
        
        if self.print_only:
            sys.stdout.write('Recipients %s\n' % recipients)            
            sys.stdout.write('%s\n\n\n\n\n' % msg)
            return

        if self.ccs:
            recipients.extend(self.ccs)
        if self.bccs:
            recipients.extend(self.bccs)
        if self.test_to != None:
            sys.stderr.write('Would send email to: %s\n' % recipients)
            recipients = [self.test_to]
        sys.stderr.write('Sending email to: %s\n' % recipients)
            
        s = self.get_smtp() 

        success = False
        print "Recipients is %s" % (recipients)
        try:
            s.sendmail(msg['From'], recipients, msg.as_string())
            success = True
        except smtplib.SMTPRecipientsRefused as err:
            sys.stderr.write('SMTP Recipients Refused:\n')
            sys.stderr.write('%s\n' % str(err))
        except smtplib.SMTPException:
            sys.stderr.write('Error sending to %s ...\n' % recipients)
            raise
        finally:
            self.message_sent(success, len(recipients))

    def get_smtp(self):
        if self.smtp == None:
            self.smtp = smtplib.SMTP(self.smtp_server)
            self.smtp.set_debuglevel(self.debug)
            if self.start_tls:
                self.smtp.starttls()
            if self.auth_user is not None:
                self.smtp.login(self.auth_user, self.auth_passwd)
            self.msgs_tried = 0
        return self.smtp

    def message_sent(self, success, nos_recipients):
        self.msg_tries = self.msg_tries + 1
        if success:
            self.all_msgs_sent = self.all_msgs_sent + 1
            self.all_copies_sent = self.all_copies_sent + nos_recipients
            # Crude rate limiting
            if self.delay_after_send:
                time.sleep(self.delay_after_send)
        if self.msg_tries > self.max_tries:
            self.smtp.quit()
            self.smtp = None
        
    def render_and_send(self, user=None, group=None):
        subject = self.generator.render_subject(user, group,
                                                self.db, self.config)

        text_frags, html_frags = \
            self.generator.generate_frags(user, group,
                                          self.db, self.config)
        if not html_frags:
            html_frags = text_frags
        text, html = self.generator.render_templates(user, group,
                                                     self.db, self.config,
                                                     subject, text_frags,
                                                     html_frags)
        if not subject or len(subject.strip()) == 0:
            raise Exception('Empty subject')
        if user != None:
            if user['email'] is not None:
                self.send_email([user['email']], subject, text, html)
        else:
            emails = map(lambda u: u['email'], group['users'].values())
            self.send_email(filter(lambda e: e is not None, emails),
                            subject, text, html)
