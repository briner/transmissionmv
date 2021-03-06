#!/usr/bin/env python

import os
import sys
import argparse
import re

try:
    import transmissionrpc
except:
    print("Unable to 'import transmissionrpc' !")
    print("Create a venv for this:")
    print(" - python3 -m venv venv")
    print(" - source venv/bin/activate")
    print(" - pip install -r requirements.txt")
    print("To debug install also:")
    print(" - pip install ipython")
    print("Exit !")
    sys.exit(1)


# COMMON

def get_client():
    print("Check that we can connect to localhost")
    try:
        client = transmissionrpc.Client('localhost', port=9091)
    except:
        print("Unable to instantiate a client to 'localhost:9091'.")
        print(" Uncheck 'Use authentication' in Transmission > Edit preferences > Remote.")
        print(" Check that 127.0.0.1 is allowed in 'Only allow these remote addresses'.")
        print("Exit !")
        sys.exit(1)
    return client

# MOVE DIRECTORY

def get_torrent_location(torrent):
    return torrent._fields["downloadDir"].value

def is_elligible_for_location_move(torrent, base_dir):
    downloadDir_field = torrent._fields["downloadDir"]
    dirty = downloadDir_field.dirty
    location = downloadDir_field.value
    if dirty:
        return False
    if location.find(base_dir) != 0:
        return False
    return True


def move_directory(tc, torrent, cur_dir, new_dir):
    cur_location = get_torrent_location(torrent)
    first_file = torrent.files()[0]["name"]
    if not is_torrent_elligible(torrent, cur_dir):
        print("Torrent id({}), named({}), dir({})".format(torrent.id,
                                                          first_file[:20],
                                                          cur_location))
        print(" is not elligible for a move from ({}) to ({})".format(cur_dir,
                                                                      new_dir))
        print(" Skip it !")
        return
    new_location = cur_location.replace(cur_dir, new_dir)
    subdir = cur_location.replace(cur_dir, "")
    #
    if not os.path.isdir(new_location):
        print("create dir({})".format(new_location))
        os.makedirs(new_location)
    print("- move torent_id({}), named({}), subdir({})".format(torrent.id,
                                                               first_file[:20],
                                                               subdir))
    print("  to {}".format(new_location))
    tc.move_torrent_data(torrent.id, new_location, timeout=3600.0)
    return True

# TRACKER


# MAIN

def main_move_directory(cur_base_dir, new_base_dir):
    # test the arguments
    if not os.path.isdir(args.current_base_dir):
        print("current_base_dir({}) must exist !".format(args.current_base_dir))
        print("Exit !")
        sys.exit(1)
    if not os.path.isdir(args.new_base_dir):
        print("new_base_dir({}) must exist !".format(args.new_base_dir))
        print("Exit !")
        sys.exit(1)
    tc=get_client()
    lt = tc.get_torrents()
    lt_in_base = [t for t in lt if is_elligible_for_location_move(t, cur_base_dir)]
    for t in lt_in_base:
        move_directory(tc, t, cur_base_dir, new_base_dir)

def main_tracker_list(announce_re_str):
    tc=get_client()
    lt = tc.get_torrents()
    announce_re=re.compile(announce_re_str)
    lannounce=[]
    for t in lt:
        announce=t._fields["trackers"].value[0]["announce"]
        if announce_re.search(announce):
            lannounce.append(announce)
    lannounce=set(lannounce)
    print(os.linesep.join(lannounce))

def main_tracker_move(announce_re_str, new_announce,
                      dry_run, verbose, fullname):
    tc=get_client()
    lt = tc.get_torrents()
    announce_re=re.compile(announce_re_str)
    lannounce=[]
    if verbose:
        print("id", "file_name")
    for t in lt:
        announce=t._fields["trackers"].value[0]["announce"]
        if not announce_re.search(announce):
            continue
        if verbose:
            if fullname:
                print(t.id, t.name)
            else:
                print(t.id, t.name[:70])
        if not dry_run:
            tc.change_torrent(t.id,trackerReplace=(0,new_announce))

if "__main__" == __name__:
    parser = argparse.ArgumentParser(description="tool to manage transmission")
    subparsers = parser.add_subparsers(help='sub-command help')

    # move-dir
    parser_location= subparsers.add_parser('move-directory', help='move directory')
    parser_location.add_argument("current_base_dir")
    parser_location.add_argument("new_base_dir")

    # traker
    parser_tracker = subparsers.add_parser("tracker", help="manage tracker")
    subparser_tracker = parser_tracker.add_subparsers(help='sub-command help')
    # tracker list
    parser_tracker_list = subparser_tracker.add_parser("list")
    parser_tracker_list.set_defaults(cmd="tracker-list")
    parser_tracker_list.add_argument('re', metavar='re', default=".*",
                                     type=str, nargs='?',
                                     help='regular expression')
    # tracker move
    parser_tracker_move = subparser_tracker.add_parser("move")
    parser_tracker_move.set_defaults(cmd="tracker-move")
    parser_tracker_move.add_argument('re', metavar='re', default=".*",
                                     type=str, help='regular expression')
    parser_tracker_move.add_argument("new_announce")
    parser_tracker_move.add_argument("-n", "--dry_run", dest="dry_run",
                                     action="store_true", default=False)
    parser_tracker_move.add_argument("-v", "--verbose", dest="verbose",
                                     action="store_true", default=False)
    parser_tracker_move.add_argument("--fullname", dest="fullname",
                                     action="store_true", default=False)
    args = parser.parse_args()

    if not hasattr(args,"cmd"):
        parser.print_usage()
    elif args.cmd == "tracker-list":
        main_tracker_list(args.re)
    elif args.cmd == "tracker-move":
        main_tracker_move(args.re, args.new_announce, args.dry_run, args.verbose,
                          args.fullname)
    elif args.cmd == "move-directory":
        main_move_directory(args.current_base_dir, args.new_base_dir)
