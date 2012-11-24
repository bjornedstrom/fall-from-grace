# fall-from-grace
November 24, 2012

`fall-from-grace` is a non-intrusive userspace process supervisor.

It runs on the side of existing processes, rather than below them (in contrast with, for example, `supervisord` or `daemontools`).

This is very early work in progress.

# Rationale

Judge, jury and executioner specifically designed to gracefully terminate non-service processes (web browsers, media players...) leaking memory. Can easily be adapted for other triggers.

It is written because I have not had great success with the standard unix facilities, such as setting resource limits, or tweaking the OOM killer (see my other project [oomtools](https://github.com/bjornedstrom/oomtools))

# Install & Run

You can

    $ python setup.py build

And then install `init.d` script `debian/init` by hand.

Otherwise:

    $ debuild

The program depends on `psutil` and `daemon` (debian packages python-psutil, python-daemon)

For development, run neat:

    $ ./bin/fall-from-grace

For normal usage, control with `init.d`.

# Configuration

TODO: document this further.

`/etc/fall-from-grace.conf`:

    {
        "monitor": {
            "conkeror": {
                "cmdline": "xulrunner-bin .*conkeror",
                "actions": {
                    "rmem > 1073741824": "term"
                }
            }
        }
    }

Config can be reloaded by `init.d` or by sending SIGHUP.

# Administration

`fall-from-grace` will log interesting events to syslog.

# License

This software is written by Björn Edström 2012. See LICENSE for details.
