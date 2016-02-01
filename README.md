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

How to use:

This tool is powerful and potentially dangerous.  It can send a large
number of emails to a large number of people in a short time.  If you make
a mistake, it could be very embarrassing.

Therefore I recommend the following workflow:

  1. Think carefully about who the emails need to go to.  Try to restrict them
     to the users who really need to know, and bear in mind that some people
     may potentially have multiple "affected" resources.

  2. Draft a template email.

  3. Figure out which subcommand is most appropriate for selecting the
     affected resources and the target users.

  4. Test the selection by running the mailout **without the `-y` option**.
     (TBD - functionality for showing you the target users, etc)

  5. Test the template expansion by running the mailout with
     `-y -P --limit <N>`.  This will generate the first `<N>` emails and
     write them to standard output.

  6. Check the mailer configs.  Depending on the outgoing server you are
     using, you may need to limit the rate of mail sending, etcetera.
     For instance, the UQ mailer will throttle mailouts if you submit
     more than one email per second.

  7. Try the mailout sending just 1 email to your own email address.  You
     can use `-T` to override the target for all emails.

  8. Touch wood.

  9. Start the mailout for real with `-y` ...
  

References:

The mailout tool uses the Jinja2 templating engine for processing mail
templates.  The templating language syntx and semantics are documented
in the Template Designer Documentation:

  - http://jinja.pocoo.org/docs/dev/templates/
