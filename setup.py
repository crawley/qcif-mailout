from setuptools import setup

setup(name='qcif-mailout',
      version='0.1',
      description='The QCIF Ops mailout tool',
      url='http://github.com/crawley/qcif-mailout',
      author='Stephen Crawley',
      author_email='s.crawley@uq.edu.au',
      license='MIT',
      packages=['mailout'],
      install_requires=[
          'jinja2',
          'python-novaclient<=3.2.0',
          'python-neutronclient<=4.2.0',
          'python-keystoneclient<=2.3.1'
      ],
      zip_safe=False)
