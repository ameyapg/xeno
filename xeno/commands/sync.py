# System imports
from sys import exit
import sys
import os
import argparse
import uuid
from shutil import rmtree
import signal
import time

# xeno imports
from xeno.core.output import print_error
from xeno.core.configuration import get_configuration, string_to_bool
from xeno.core.paths import get_working_directory
from xeno.core.git import clone, add_metadata_to_repo, \
    sync_local_with_remote, self_destruct_remote
from xeno.core.sessions import get_sessions, XENO_SESSION_LOCAL_PROCESS_ID, \
    XENO_SESSION_LOCAL_REPOSITORY_PATH, XENO_SESSION_REMOTE_IS_FILE


def parse_arguments():
    """Method to parse command line arguments.

    This function will parse command line arguments using the argparse module.

    Returns:
        A namespace of the arguments.
    """
    # Set up the core parser
    parser = argparse.ArgumentParser(
        description='synchronize a xeno session with the remote',
        usage='xeno-sync [-h|--help] session',
    )

    # Add arguments
    parser.add_argument('--daemonize',
                        action='store_true',
                        help=argparse.SUPPRESS)
    parser.add_argument('--remote-path',
                        action='store',
                        nargs=1,
                        help=argparse.SUPPRESS,
                        dest='remote_path')
    parser.add_argument('--remote-is-file',
                        action='store_true',
                        help=argparse.SUPPRESS,
                        dest='remote_is_file')
    parser.add_argument('--clone-url',
                        action='store',
                        nargs=1,
                        help=argparse.SUPPRESS,
                        dest='clone_url')
    parser.add_argument('--foreground',
                        action='store_true',
                        help=argparse.SUPPRESS)
    parser.add_argument('session',
                        help='the session number to synchronize (the first '
                             'column in \'xeno list\')',
                        action='store',
                        nargs='?')

    # Parse arguments
    args = parser.parse_args()

    # Check if we are a daemon, and if so validate other arguments
    if args.daemonize:
        if args.remote_path is None:
            print_error('Remote path must be specified for daemon mode')
            exit(1)
        if args.clone_url is None:
            print_error('Clone URL must be specified for daemon mode')
    else:
        # If we are not a daemon, and there is no session specified, print help
        # and exit
        if args.session is None:
            parser.print_help()
            exit(1)

    # Do the parsing
    return parser.parse_args()


def daemonize():
    """Forks the process into a daemon.

    This method uses the UNIX double-fork trick to ensure the daemon process
    is attached to init and does not reacquire a TTY.  This method only returns
    in the second forked process.
    """
    # TODO: Add some more error checking in here...

    # Do the first fork
    if os.fork() > 0:
        # This is the first parent, exit calmly
        # Recommended exit method on fork()
        os._exit(0)

    # We must be in the first child, decouple from the original parent
    os.chdir('/')
    os.setsid()
    os.umask(0)

    # Do the second fork
    if os.fork() > 0:
        # This is the intermediate, exit calmly
        # Recommended exit method on fork()
        os._exit(0)

    # Otherwise, we're in the second child, set our outputs and keep going...
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')


def main():
    """The sync subcommand handler.

    This method handles the 'sync' subcommand by forking off a daemon to watch
    a particular local repository and synchronize back to the remote.
    """
    # Load configuration
    configuration = get_configuration()

    # Parse arguments
    args = parse_arguments()

    # Check if we are running in daemon mode.  If not, then we are just doing
    # a single sync.  Try to identify the specified session.
    if not args.daemonize:
        # Convert the session id
        try:
            pid = int(args.session)
        except:
            print_error('Invalid session id: {0}'.format(args.session))
            exit(1)

        # Grab all sessions
        sessions = get_sessions()

        # Find our session
        for session in sessions:
            # Grab the metadata
            process_id = session[XENO_SESSION_LOCAL_PROCESS_ID]

            # Check if it matches
            if pid == process_id:
                # Do a sync
                result = sync_local_with_remote(
                    session[XENO_SESSION_LOCAL_REPOSITORY_PATH],
                    True,  # Poll the remote
                    session[XENO_SESSION_REMOTE_IS_FILE]
                )

                # Show the result and exit
                if not result:
                    print_error('Unable to complete sync')
                    exit(1)

                exit(0)

        # Couldn't find a match
        print_error('Couldn\'t find specified session: {0}'.format(
            args.session
        ))
        exit(1)

    # At this point, we are becoming a daemon.  Extract arguments.
    remote_is_file = args.remote_is_file
    remote_path = args.remote_path[0]
    clone_url = args.clone_url[0]

    # Grab the working directory
    working_directory = get_working_directory()

    # Create a unique directory we can use as the PARENT of the repo
    repo_container = os.path.join(working_directory,
                                  'local-' + uuid.uuid4().hex)
    try:
        os.makedirs(repo_container, 0o700)
    except:
        print_error('Unable to create repository parent')
        exit(1)

    # Figure out what we're going to call the repo directory.  We have to do
    # normpath call here because if remote_path contains a trailing /, the
    # basename will be empty.
    repo_directory_name = \
        ('remote'
         if remote_is_file
         else os.path.basename(os.path.normpath(remote_path)))
    repo_path = os.path.join(repo_container, repo_directory_name)

    # Clone the remote URL
    clone(clone_url, repo_path)

    # Set metadata on the local repo
    add_metadata_to_repo(repo_path, 'remoteIsFile', str(remote_is_file))
    add_metadata_to_repo(repo_path, 'remotePath', remote_path)

    # Print the editable path.
    # HACK: We have to flush, because the daemon process will inherit the same
    # file descriptors and since they are never closed, this line may remain
    # buffered indefinitely, causing anyone waiting for the output to wait
    # for-ev-er.
    if remote_is_file:
        print(os.path.join(repo_path, os.path.basename(remote_path)))
    else:
        print(repo_path)
    sys.stdout.flush()

    # Daemonize (unless told not to)
    if not args.foreground:
        daemonize()

    # We are the daemon (or the original process if we didn't daemonize).  Add
    # our process id to the remote metadata
    add_metadata_to_repo(repo_path, 'syncProcessId', str(os.getpid()))

    # Create a cleanup method
    def cleanup():
        # Do a push to the remote that'll cause it to self-destruct
        self_destruct_remote(repo_path)

        # Remove our own repository
        rmtree(repo_container)

    # We are the daemon!  Set up the signal handler for easy exit
    def signal_handler(signum, frame):
        # Cleanup and exit
        cleanup()
        exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Calculate our sync interval
    sync_interval = 10
    if configuration.has_option('sync', 'syncInterval'):
        try:
            sync_interval = int(configuration.get('sync', 'syncInterval'))
        except:
            # Just go with the default interval
            pass

    # Calculate whether or not to poll the remote
    poll_remote = False
    if configuration.has_option('sync', 'pollForRemoteChanges'):
        try:
            poll_remote = string_to_bool(
                configuration.get('sync', 'pollForRemoteChanges')
            )
        except:
            # Invalid value...
            pass

    # Enter our main loop
    while True:
        # Do the sync
        sync_local_with_remote(repo_path,
                               poll_remote,
                               remote_is_file)

        # Sleep
        time.sleep(sync_interval)

    # All done (unreachable code, but whatever)
    exit(0)
