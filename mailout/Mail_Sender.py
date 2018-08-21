from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
import argparse
import csv
import os
import sys
import smtplib
import time

from Sender import Sender

class Mail_Sender(Sender):

    def __init__(self, *args, **kwargs):
        Sender.__init__(self, *args, **kwargs)
        self.auth_user = self._get_optional('SMTP', 'auth-user')
        self.auth_passwd = self._get_optional('SMTP', 'auth-password')
        self.smtp_server = self.config.get('SMTP', 'server')
        self.smtp_port = int(self._get_optional('SMTP', 'port', dflt="25"))
        self.start_tls = self.config.getboolean('SMTP', 'start-tls')
        if self.auth_user is not None and not self.start_tls:
            raise Exception("Insecure!  Don't specify an auth-user without start-tls")
        self.smtp = None
        self.max_tries = self.config.getint('SMTP', 'max-tries-per-connection')
        self.rate = self.config.getfloat('SMTP', 'max-messages-per-second')
        self.delay_after_send = 1.0 / self.rate if self.rate else None
        if self.debug:
            sys.stderr.write('Mail_Sender: %s\n' % self.__dict__)


    @staticmethod
    def init_config(config):
        Sender.init_config(config)
        config.add_section('SMTP')
        config.set('SMTP', 'server', '127.0.0.1')
        config.set('SMTP', 'port', '25')
        config.set('SMTP', 'max-tries-per-connection', 100)
        config.set('SMTP', 'max-messages-per-second', 1.0)
        config.set('SMTP', 'auth-user', None)
        config.set('SMTP', 'auth-password', None)
        config.set('SMTP', 'start-tls', True)

    def send_message(self, recipients, subject, text, html=None):
        if not self.presend_checks(recipients, subject, text, html):
            return
        
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
            self.smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            self.smtp.set_debuglevel(self.debug)
            if self.start_tls:
                self.smtp.starttls()
            if self.auth_user is not None:
                self.smtp.login(self.auth_user, self.auth_passwd)
            self.msgs_tried = 0
        return self.smtp

