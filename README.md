xeno
====
[xeno](https://xeno.io/) is a tool that enables remote file and folder editing
over SSH using your local text editor of choice, be it command line or
GUI-based.

For more information, please see the introductory site: 
[https://xeno.io/](https://xeno.io/)


Features and Basic Usage
------------------------
To start editing a remote path over SSH, use

    xen user@hostname:/the/path

xeno will clone the remote path locally and keep it in sync with the remote
copy.  Or, if you are already in an SSH session<sup>1</sup>, you can do

    xen /the/path

and it will have exactly the same effect!

<sup>
1: For in-session launches, you must use `xeno ssh`, a VERY thin wrapper around
SSH which monitors console output for initialization messages
([FAQ](https://github.com/havoc-io/xeno/wiki/FAQs#isnt-it-insecure-to-use-the-xeno-ssh-wrapper)).
</sup>


How Does it Work?
-----------------
When xeno is invoked, it will generate an out-of-work-tree Git repository on the
remote machine to track and coordinate changes.  xeno will then clone the remote
repository, launch your local editor on the clone, and launch a daemon to keep
the local and remote in-sync.

Because the remote Git repository is outside of the work tree, you can use it to
edit remote folders which may already be Git repositories without any conflicts.
xeno also works for editing single remote files.  Best of all, because it uses
Git, it will safely merge changes to and from the remote, and if your local
editor is Git-aware, it will show you which files have or haven't been synced to
the remote.

xeno provides a variety of commands for starting, managing, resuming, and ending
sessions.  xeno is robust, and the daemon will continue trying to sync changes
to the remote repository even if SSH access becomes temporarily unavailable.
When the editing session is ended, xeno will automatically clean up all local
and remote resources.


Extended Usage
--------------
To view help information, use

    xeno --help

xeno uses a variet of subcommands to do its bidding (e.g. config, edit, ...).
To view help information for a particular subcommand, use:

    xeno SUBCOMMAND_NAME --help

xeno supports the following subcommands:

- [__edit__](https://github.com/havoc-io/xeno/wiki/edit): Starts editing sessions
- [__config__](https://github.com/havoc-io/xeno/wiki/config): Manages xeno configuration information
- __ssh__: A pass-through to 'ssh' which monitors console output for session initialization
  ([see FAQ](https://github.com/havoc-io/xeno/wiki/FAQs#isnt-it-insecure-to-use-the-xeno-ssh-wrapper)).
- [__list__](https://github.com/havoc-io/xeno/wiki/list): Lists active xeno sessions
- [__resume__](https://github.com/havoc-io/xeno/wiki/resume): Resumes a xeno session (open your editor on the local copy)
- [__stop__](https://github.com/havoc-io/xeno/wiki/stop): Stops a xeno session and cleans up local/remote resources
- [__sync__](https://github.com/havoc-io/xeno/wiki/sync): Syncs a xeno session with the remote copy (automatically run as a
  daemon when using xeno edit to do periodic synchronization, and also available
  to manually push/pull changes on-demand)

For convenience, the `xeno edit` command is aliased as `xen`.  To keep
consistency, if you use the `xeno edit` command on a local path, it will simply
open the local path in your editor, so you don't have to use a different command
to launch your local editor.


Configuration
-------------
xeno's configuration is managed via the 'xeno config' command.  Configuration
values can be set with:

    xeno config key value

Configuration values can be viewed with:

    xeno config key

Configuration values can be cleared with:

    xeno config key --clear

xeno supports the following configuration keys:

- __core.editor__: The editor command to use.  If not set, xeno will fall back
  to the EDITOR environment variable.
- __core.workingDirectory__: The directory where xeno should store its local
  copies of repositories.  If not set, xeno will use ~/.xeno.
- __sync.syncInterval__: The period, in seconds, to wait between checks for
  local changes.  The default is 10.
- __sync.pollForRemoteChanges__: By default, xeno only checks for changes on the
  remote when pushing local changes.  If this is set to True, xeno will check
  the remote for changes every time it checks the local copy.


Extending xeno
--------------
Like Git, xeno can be readily extended without modifying the source.  When xeno
receives a subcommand with the name `SUBCOMMAND`, it will look for an executable
in the PATH variable with the name `xeno-SUBCOMMAND`.  If one is found, xeno
will pass through all command-line arguments through to the subcommand.


Requirements
------------
- POSIX-based operating system (I'll happily review pull requests for Windows)
- Python 2.7+ (Including Python 3.2+, although please report bugs)
- Git
- OpenSSH


Installation
------------
The easiest (and only supported) way of installing xeno is using pip:

    pip install git+https://github.com/havoc-io/xeno.git@0.0.4

xeno needs to be installed on both ends of the editing connection.  You also
need to have pip's console_scripts install directory in your path for both login
AND non-login shells.  Adding the path to your login shell is pretty easy and
likely on by default.  Non-login shells usually require an entry in your
`~/.bashrc` or `~/.zshenv` file.

It is important to note that on some systems, e.g. Ubuntu, there is a statement
in the default ~/.bashrc to prevent it from being run for non-interactive
shells, so you either need to remove this statement or add the path statement
before that. It typically looks something like:

    # If not running interactively, don't do anything
    case $- in
        *i*) ;;
        *) return;;
    esac

For other shells, best to consult documentation.

Also, if you want in-session launch capabilities, you need to do:

    alias ssh="xeno ssh"

The `xeno ssh` command is just a pass-through to SSH, but it monitors SSH's
console output for initialization tokens.  If this is a little too
tin-foil-hat-inducing for you, you can still use the local launch mechanism
without losing any sleep.  For more information, please see the
[FAQ](https://github.com/havoc-io/xeno/wiki/FAQs#isnt-it-insecure-to-use-the-xeno-ssh-wrapper)
on this topic.


More Information
----------------
For more detailed information, please see the
[xeno wiki](https://github.com/havoc-io/xeno/wiki) and
[FAQs](https://github.com/havoc-io/xeno/wiki/FAQs).


TODO List
---------
- Make xeno work with tmux/screen.  At least with tmux, xeno-init messages come
  across every time the buffer is refreshed and new sessions are launched.
- Add --all option to sync
- Add option to kill off sessions automatically after some period of inactivity
- Make session ids nicer, add central registry to avoid confusing PIDs
- Perhaps alternatively, make resume accept a string argument and do a search
  for the best-matching path.  In the case of ambiguity, require a session id.
- Add core.debug setting
- Modify output to use Python's logging system
- Replace local polling with `watchdog` or a similar file-monitoring library
- Finish Windows support
- Fix all code TODOs and HACKs
