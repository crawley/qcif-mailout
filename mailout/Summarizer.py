import argparse
import csv
import os
import sys
import smtplib
import time

class Summarizer:

    def __init__(self, config, db, generator, debug=False):
        self.db = db
        self.generator = generator
        self.config = config
        self.debug = debug

    def render_and_send(self, user=None, group=None):
        '''
        This simply renders the templates and writes the text version to standard error.
        The intended use-case is for generating a formatted summary broken down by 
        email recipient or group.
        '''

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
        sys.stdout.write(text)
