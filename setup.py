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
          'python-novaclient<3.0',
          'python-neutronclient',
          'python-keystoneclient>=3.0',
          'mysql-connector-python'
      ],
      zip_safe=False)
