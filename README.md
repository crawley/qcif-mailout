Prerequisites

You need python 2 with setuptools.  Using "virtualenv" is recommended:

  - Install the "python-devel" and "python-virtualenv" packages or equivalent
    using your distro's package installer.

  - Create and activate a "venv"

Installation from source:

  - Clone the master GIT repo.

  - To create the development sandbox:

    - cd to the git tree
    - run "python setup.py develop"
    - run "mailout/mailout.py" ... and you should get the basic usage info.


  - To install mailout (e.g. into your venc)

    - run "python setup.py install"

Basic documentation:

The purpose of the command is to perform mailouts to users of QRIScloud
facilities.  The process typically involves

  - specifying / selecting a set of resources,
  - extracting the information about them from various places (NeCTAR
OpenStack, NeCTAR Allocations, Candle, etc),
  - figuring out who to notify concerning each resource,
  - collating information by user,
  - formating, generating and sending individualized emails.

In addition to the code itself, the process is controlled by a configuration
file, mailout specific templates and "fragment" generators ... and the command
line arguments that control resource and target user selection.
