from jinja2 import Environment, FileSystemLoader, Template
from jinja2.exceptions import TemplateNotFound
import email

class Generator:
    def __init__(self, name, subject):
        self.template_name = name
        self.subject_template = Template(subject)
        self.env = Environment(loader=FileSystemLoader('templates'))
        self.text_template = self.env.get_template('%s.tmpl' % name)
        try:
            self.html_template = self.env.get_template('%s.html.tmpl' % name)
        except TemplateNotFound:
            self.html_template = None
        
    def render_templates(self, user, group, db, config, subject,
                         text_frags, html_frags):
        text = self.text_template.render(
            {'user': user,
             'group': group,
             'config': config,
             'db': db,
             'subject': subject,
             'frags' : text_frags})
        if self.html_template:
            html = self.html_template.render(
                {'user': user,
                 'group': group,
                 'config': config,
                 'db': db,
                 'subject': subject,
                 'frags' : html_frags})
        else:
            html = None

        return text, html

    def render_subject(self, user, group, db, config):
        '''The default behavior is to perform template expansion on the 
        subject parameter.
        '''
        return self.subject_template.render(
            {'user': user,
             'group': group,
             'db': db,
             'config': config})
        
    def generate_frags(self, user, group, db, config):
        '''The default behavior is to generate no fragments.  
        Override this method to generate fragments.  This method is
        expected to return one or two dictionaries, that map keys to
        formatted strings for inclusion in the message templates.  If
        two dictionaries are returned, the first is for the plain text
        rendering and the second one for the HTML rendering.
        '''
        return {}, None
    
