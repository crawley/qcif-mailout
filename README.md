# Introduction

The purpose of the command is to perform mailouts to users of QRIScloud
facilities.  The process typically involves:

  - specifying / selecting a set of resources,
  - extracting the information about them from various places (NeCTAR
OpenStack, NeCTAR Allocations, Candle, etc),
  - figuring out who to notify concerning each resource,
  - collating information by user or by "group"
  - formating, generating and sending individualized emails.

In addition to the code itself, the process is controlled by a configuration
file, mailout specific templates, and command line arguments that control
resource and target user selection.

The tool is intended to be extensible, but this aspect is a work in progress.

# Installation

## Prerequisites

You need python 2 with setuptools.  Using "virtualenv" is recommended:

  - Install the "python-devel" and "python-virtualenv" packages or equivalent
    using your distro's package installer.

  - Create and activate a venv; e.g. run "virtualenv venv"

  - Install mysql-connector-python.  (Blame Oracle for the fact that you can't
    get it from Pypi like you used to ...)

    - clone the source tree for "mysql/mysql-connector-python" from github.
    - cd to the git tree
    - run "python setup install" to install into your venv.
      

## Installation from source:

  - Clone source from the master GIT repo.

  - To create the development sandbox:

    - cd to the git tree
    - run "python setup.py develop"
    - run "mailout/mailout.py" ... and you should get the basic usage info.

  - To install mailout (e.g. into your venv)

    - run "python setup.py install"

# Command syntax

The general syntax is:

```
mailout <global options> <command> <command-specific options>
```

The following commands are currently available:

  - `help` - command self-documentation
  - `instances` - use a set of NeCTAR instances as the resources to
    drive the mailout for the mailout.  User and tenant information is
    fetched from Keystone.
  - `csv` - use a CSV file as the source of user information
  - `db` - use a MySQL / MariaDB database query as the source of user
    information
  - `write-skeleton-config` - just generates a skeleton config file.

The global options are:

  - `--by-group` - collate resources by "group" and generate one email per
    group with multiple recipients.  The default is to generate one email
    per user.
  - `-c` `--config` `<file>` - selects a config file.  This defaults to
    `~/.mailout.cfg`.
  - `-d` `--debug` - enables extra debugging.  For example, this allows you
    to see OpenStack requests and responses.
  - `-l` `--limit` `<number>` - limits the number of emails to be processed.
    The default is no limit.  (This option is intended primarily for testing
    out your mailout's selection and templating.)
  - `-P` `--print-only` - emails are "printed" to standard output, not sent.
  - `-s` `--subject` `<subject>` - provide a subject for the emails, overriding
    the subject (if any) in the config file.  The subject should be quoted.
    You can include templating markup.
  - `--skip-to` `<key>` - skip over users (or groups) until we get to the
    one denoted by the key.  This is for resuming a mailout that died / was
    killed part-way through.
  - `-t` `--template` `<basename>` - the basename for the mailout's templates.
    This defaults to `template`.
  - `-T` `--test-to` `<email>` - emails are sent to the supplied email
    address, rather than the (ultimate) intended recipient addresses.
  - `-y` `--no-dry-run` - do the email processing.  The default in dry-run
    mode which simply does the resource and user selection, extraction
    and collation.
  

# Advice on safe use

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

  9. Start the mailout for real with `-y` ... and make sure that you capture
     the output so that you can "resume" the mailout in the event of a failure.
  

References:

The mailout tool uses the Jinja2 templating engine for processing mail
templates.  The templating language syntx and semantics are documented
in the Template Designer Documentation:

  - http://jinja.pocoo.org/docs/dev/templates/
