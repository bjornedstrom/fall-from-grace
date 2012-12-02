# fall-from-grace - a non-intrusive userspace process supervisor
0.1.0-rc2, November 2012

`fall-from-grace` is a userspace daemon that monitors processes for certain triggers and acts on those. For example, it can monitor your web browser and kill it if it uses too much memory. It runs on the side of existing processes, rather than below them (in contrast with, for example, `supervisord` or `daemontools`).

This software is currently very early work in progress.

### Features

* Can monitor specific processes by regular expression on program command lines.
* Can monitor child processes, recursively.
* Can trigger on memory usage, virtual and residential.
* Actions include some reasonable signals: SIGSTOP (very useful to suspend a process leaking memory), SIGTERM, SIGKILL.
* Can execute a program on trigger, with some variable expansions (see below).
* Actions can be rate limited, for example the action runs at most once per hour.
* Simple YAML and rules based configuration language.
* Adhers to reasonable standards how a daemon should behave (SIGHUP reloads config file, interesting events are sysloged).
* Written in Python makes it easy to extend for your need.
* Reasonably small memory footprint and low resource usage.
* init.d script provided.
* Debian packaged.

## Install & Run

If you are on a Debian based distribution, it is easiest to just build and install the Debian package:

    $ debuild

Otherwise, you can;

    $ python setup.py build

And then install `init.d` script `debian/init` by hand.

### Dependencies

The program depends on:

- `psutil` ([psutil](http://code.google.com/p/psutil/)).
- `daemon` ([python-daemon](http://pypi.python.org/pypi/python-daemon/)).
- `yaml` ([PyYaml](http://pyyaml.org/)).
- `ply` ([ply](http://www.dabeaz.com/ply/)).
- `mock` ([Mock](http://www.voidspace.org.uk/python/mock/) for unit testing).

All of the above projects have Debian packages, see `debian/control` for names.

### Run

For development, run neat:

    $ PYTHONPATH=. ./bin/fall-from-grace

For normal usage, control with `init.d`.

## Configuration & Administration

NOTE: This config format is much likely to change during development.

fall-from-grace is (typically) configured in the single configuration file `/etc/fall-from-grace.conf`. Each process to monitor has a YAML fragment, as below:

    conkeror:
      cmdline: xulrunner-bin .*conkeror
      children: 1 # optionally check all children, defaults to false
      final: 1 # see below for details
      actions:
        rmem > 500m: exec notify-send "conkeror is using too much ram"
        rmem > 900m: term

The first line (`conkeror`) is a single human-readable name for the process, used for logging. `cmdline` is a regex that will match on the process cmdline. `actions` is a list of triggers and actions to take.

### Triggers

Here are some examples of valid triggers:

    rmem > 1g
    1g < rmem
    vmem > 900m
    rmem > 2097152

Where `rmem` and `vmem` means residential and virtual memory, respectively.

### Actions

Here are some examples of valid actions:

    term
    kill
    stop @ 10m
    exec logger "program is using too much ram"
    exec logger "$NAME ($PID) is using too much ram"
    exec @ 1h logger "$NAME ($PID) is using too much ram"

The last form (`exec @ TIME`) means the program will be run at most once per hour.

SIGSTOP always has the form `stop @ TIME` to give the user time to CONT and then act accordingly.

### Administration

Config can be reloaded by `init.d` or by sending SIGHUP.

`fall-from-grace` will log interesting events to syslog.

### Advanced configuration

In addition to `/etc/fall-from-grace.conf`, the program will also pick up files, if they exist, from `/etc/fall-from-grace.d`. If both the .conf file exists and files in the dot-d directory exists, the result is concatenated with the .conf file first. The files in the dot-d directory follow the usual standards (files with a name of the form NN-foobar will appear higher in the concatenated result if NN is high).

Note that fall-from-grace will actually read the resulting YAML string as an ordered dict, instead of an unordered. This is used so a monitor with high prio will be executed first. By default, all monitors that trigger on a certain pid will be executed in order, so you can have two monitors matching the same cmdline and both will be run. If this is undesirable, you can set the "final" keyword on a monitor fragment. In that case, subsequent monitors that could match the same cmdline will not be executed.

## About & License

This software is written by Björn Edström 2012. See LICENSE for details.

The author wrote the software because he did not have great success with the standard Unix facilities, such as setting resource limits, or tweaking the OOM killer (see the authors other project [oomtools](https://github.com/bjornedstrom/oomtools)).
