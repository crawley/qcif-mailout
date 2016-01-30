from setuptools import setup

setup(name='qcif-mainout',
      version='0.1',
      description='The QCIF Ops mailout tool',
      url='http://github.com/crawley/qcif-mailout',
      author='Stephen Crawley',
      author_email='s.crawley@uq.edu.au',
      license='MIT',
      packages=['mailout'],
      install_requires=[
          'jinja2',
          'python-novaclient',
          'python-keystoneclient'
      ],
      zip_safe=False)
