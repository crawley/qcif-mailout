import argparse
import csv
import os
import sys
import time

class Sender:

    def __init__(self, config, db, generator, print_only=False,
                 debug=False, limit=None, test_to=None, ccs=[], bccs=[]):
        self.db = db
        self.generator = generator
        self.config = config
        self.from_addr = config.get('Envelope', 'from')
        self.sender = config.get('Envelope', 'sender')
        self.reply_to = config.get('Envelope', 'reply-to')
        self.ccs = self._get_defaults_and_fix(ccs, 'cc')
        self.bccs = self._get_defaults_and_fix(bccs, 'bcc')
        self.print_only = print_only
        self.debug = debug
        self.test_to = test_to
        self.limit = limit
        self.msg_tries = 0
        self.all_msgs_sent = 0
        self.all_copies_sent = 0
        self.encoding = config.get('Body', 'encoding')
        self.plain_only = config.getboolean('Body', 'plain-only')
        self.html_only = config.getboolean('Body', 'html-only')
        self.hide_recipients = config.getboolean('Envelope', 'hide-recipients')
        self.need_html = False
        
    def _get_optional(self, section, option, dflt=None):
        if self.config.has_option(section, option):
            res = self.config.get(section, option)
            return dflt if res is None else res
        else:
            return dflt

    def _get_defaults_and_fix(self, list, config_key):
        if list == None or len(list) == 0:
            list = [ self._get_optional('Envelope', 'cc', dflt="") ]
        # Some SMTP servers do not like empty recipient emails at all
        return filter((lambda e: e and e != ""), list)

    @staticmethod
    def init_config(config):
        if not config.has_section('Envelope'):
            config.add_section('Envelope')
        config.set('Envelope', 'from',
                   'NeCTAR Research Cloud <bounces@rc.nectar.org.au>')
        config.set('Envelope', 'sender', None)
        config.set('Envelope', 'cc', None)
        config.set('Envelope', 'bcc', None)
        config.set('Envelope', 'reply-to', 'support@rc.nectar.org.au')
        config.set('Envelope', 'subject', None)
        config.set('Envelope', 'hide-recipients', False)
        if not config.has_section('Body'):
            config.add_section('Body')
        config.set('Body', 'encoding', 'ASCII')
        config.set('Body', 'html-only', False)
        config.set('Body', 'plain-only', False)

    def presend_checks(self, recipients, subject, text, html=None):
        if self.limit != None and self.all_msgs_sent >= self.limit:
            raise Exception('Stopping: %s messages processed / sent' %
                            self.all_msgs_sent)

        if self.html_only and html is None:
            raise Exception('The mailout config has "html-only" selected ' +
                            'but the email body generator did not find ' +
                            'an HTML template')

        # Sometimes we don't get any valid recipients ...
        if len(recipients) == 0:
            sys.stderr.write("Empty recipient list for ...\n%s\n" % text)
            return False

        return True

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
        # For some senders, an HTML version is essential.
        if html is None and self.need_html:
            html = msg.replace("\n", "<br />\n")
            html = html.replace("\s", "&#160&#160&#160&#160")
        if not subject or len(subject.strip()) == 0:
            raise Exception('Empty subject')
        if user != None:
            if user['email'] is not None:
                self.send_message([user['email']], subject, text, html)
        else:
            emails = map(lambda u: u['email'], group['users'].values())
            self.send_message(filter(lambda e: e is not None, emails),
                              subject, text, html)
