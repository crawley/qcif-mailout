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
                 debug=False, limit=None, test_to=None):
        self.db = db
        self.generator = generator
        self.config = config
        self.from_addr = config.get('Envelope', 'from')
        self.sender = config.get('Envelope', 'sender')
        self.reply_to = config.get('Envelope', 'reply-to')
        self.smtp_server = config.get('SMTP', 'server')
        self.print_only = print_only
        self.debug = debug
        self.test_to = test_to
        self.smtp = None
        self.msg_tries = 0
        self.all_msgs_sent = 0
        self.max_tries = config.getint('SMTP', 'max-tries-per-connection')
        self.rate = config.getfloat('SMTP', 'max-messages-per-second')
        self.limit = limit
        self.delay_after_send = 1.0 / self.rate if self.rate else None
        self.encoding = config.get('Body', 'encoding')
        self.plain_only = config.getboolean('Body', 'plain-only')
        self.html_only = config.getboolean('Body', 'html-only')

    @staticmethod
    def init_config(config):
        config.add_section('SMTP')
        config.set('SMTP', 'server', '127.0.0.1')
        config.set('SMTP', 'max-tries-per-connection', 100)
        config.set('SMTP', 'max-messages-per-second', 1.0)
        config.add_section('Envelope')
        config.set('Envelope', 'from',
                   'NeCTAR Research Cloud <bounces@rc.nectar.org.au>')
        config.set('Envelope', 'sender', None)
        config.set('Envelope', 'reply-to', 'support@rc.nectar.org.au')
        config.set('Envelope', 'subject', None)
        config.add_section('Body')
        config.set('Body', 'encoding', 'ASCII')
        config.set('Body', 'html-only', False)
        config.set('Body', 'plain-only', False)

    def send_email(self, recipient, subject, text, html=None):
        if self.limit and self.all_msgs_sent > self.limit:
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
        if self.test_to and not self.print_only:
            msg['X-To'] = recipient
            msg['To'] = self.test_to
        else:
            msg['To'] = recipient
        msg['Reply-to'] = self.reply_to
        if self.sender:
            msg['Sender'] = self.sender
        msg['Subject'] = subject
        
        if self.print_only:
            sys.stdout.write('%s\n\n\n\n\n' % msg)
            return

        sys.stderr.write('Sending email to: %s' % recipient)
            
        s = self.get_smtp() 

        success = False
        try:
            s.sendmail(msg['From'], [recipient], msg.as_string())
            success = True
        except smtplib.SMTPRecipientsRefused as err:
            sys.stderr.write('SMTP Recipients Refused:\n')
            sys.stderr.write('%s\n' % str(err))
        except smtplib.SMTPException:
            sys.stderr.write('Error sending to %s ...\n' % recipient)
            raise
        finally:
            self.message_sent(self, success)

    def get_smtp(self):
        if self.smtp == None:
            self.smtp = smtplib.SMTP(self.smtp_server)
            self.smtp.set_debuglevel(self.debug)
            self.msgs_tried = 0
        return self.smtp

    def message_sent(self, success):
        self.msg_tries = self.msg_tries + 1
        if success:
            self.all_msgs_sent = self.all_msgs_sent + 1
            # Crude rate limiting
            if self.delay_after_send:
                time.sleep(self.delay_after_send)
        if self.msg_tries > self.max_tries_per_connection:
            self.smtp.quit()
            self.smtp = None
        
    def render_and_send(self, user):
        text_frags, html_frags = self.generator.generate_frags(user, self.db,
                                                               self.config)
        if not html_frags:
            html_frags = text_frags
        text, html = self.generator.render_templates(user, self.db, self.config,
                                                     text_frags, html_frags)
        subject = self.generator.render_subject(user, self.db, self.config) 
        self.send_email(user['email'], subject, text, html)
        
