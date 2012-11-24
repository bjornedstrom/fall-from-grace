# fall-from-grace
November 24, 2012

`fall-from-grace` is a userspace process supervisor.

This is very early work in progress.

# Rationale

Judge, jury and executioner specifically designed to gracefully terminate processes leaking memory (but can be adapted for triggering on other aspects as well).

It is written because I have not had great success with the standard unix facilities, such as setting resource limits.

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

# Administration

`fall-from-grace` will log interesting events to syslog.

# License

This software is written by Björn Edström 2012. See LICENSE for details.
