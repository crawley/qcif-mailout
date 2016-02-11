import jinja2
import email

class Generator:
    def __init__(self, name):
        self.template_name = name
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
        self.text_template = self.env.get_template('%s.tmpl' % name)
        try:
            self.html_template = self.env.get_template('%s.html.tmpl' % name)
        except jinja2.exceptions.TemplateNotFound:
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
        '''The default behavior is to use the "subject" parameter.
        Override this method if you want to substitute values into
        the subject string.
        '''
        return config.get('Envelope', 'subject')
        
    def generate_frags(self, user, group, db, config):
        '''The default behavior is to generate no fragments.  
        Override this method to generate fragments.  This method is
        expected to return one or two dictionaries, that map keys to
        formatted strings for inclusion in the message templates.  If
        two dictionaries are returned, the first is for the plain text
        rendering and the second one for the HTML rendering.
        '''
        return {}, None
    
