import os
import sys
import importlib.metadata
from argparse import ArgumentParser, Namespace
import json
import sqlite3
import pycurl

ERROR_RED   = "[\033[0;31m ERROR \033[0m]"
WARN_YELLOW = "[\033[0;33m WARNING \033[0m]"


def fmt_list(l: list[str]) -> str:
    bullet  = "-"
    indent  = "    "
    fmt_str = f"\n{indent}{bullet} ". join(l)

    return f"\n{indent}{bullet} " + fmt_str + "\n"



def change_playist_owner_single(cursor: sqlite3.Cursor, user_id: str, playlist: str) -> None:
    """
    Changes the ownership for a single playlist. 
    
    :param cursor: Cursor object for database
    :type cursor: sqlite3.Cursor
    :param user_id: User ID, a lowercase UUID hexadecimal (without dashes)
    :type user_id: str
    :param playlists: Playlist name
    :type playlist: str
    """
    playlist_params = {
        'playlist_name': playlist, 
        'data_with_new_uid': None
    }
    
    raw_json = cursor.execute(
        """
        SELECT data 
        FROM TypedBaseItems 
        WHERE 
            type = 'MediaBrowser.Controller.Playlists.Playlist' 
            AND Name = :playlist_name
        """,
        playlist_params
    ).fetchone()

    if not raw_json:
        raise LookupError(
            f"The playlist '{playlist}' was not found in the database as given, "
            "so its ownership could not be updated. Aborting..."
        )

    # the 'data' field is a massive JSON file stored as a BLOB,
    # so it needs to be deserialized, so I can get to the correct field,
    # and then serialized again into bytes to be updated in the database
    parsed_json = json.loads(raw_json[0])
    parsed_json['OwnerUserId'] = user_id

    playlist_params['data_with_new_uid'] = json.dumps(parsed_json).encode('utf-8')
        
    
    cursor.execute(
        """
        UPDATE TypedBaseItems
        SET data = :data_with_new_uid
        WHERE 
            type = 'MediaBrowser.Controller.Playlists.Playlist' 
            AND Name = :playlist_name
        """,
        playlist_params
    )



def change_playist_owner_many(cursor: sqlite3.Cursor, user_id: str, playlists: list[str]) -> None:
    """
    Docstring for change_playist_owner_many
    
    :param cursor: Cursor object for database
    :type cursor: sqlite3.Cursor
    :param user_id: User ID, a lowercase UUID hexadecimal (without dashes)
    :type user_id: str
    :param playlists: List of playlist names
    :type playlists: list[str]
    """

    playlist_param_maps = [ 
        {'playlist_name': pl, 'data_with_new_uid': None} for pl in playlists 
    ]

    subst_qmark_str = ",".join("?"*len(playlists))
    all_pl_raw = cursor.execute(
        f"""
        SELECT name, data 
        FROM TypedBaseItems 
        WHERE 
            type = 'MediaBrowser.Controller.Playlists.Playlist' 
            AND name IN ({subst_qmark_str})
        """,
        playlists
    ).fetchall()

    # check that all playlists were found
    if len(all_pl_raw) < len(playlists):

        # okay, then which ones?
        found_playlists   = [ pl_row[0] for pl_row in all_pl_raw ]
        unfound_playlists = list(set(playlists) - set(found_playlists))
        
        raise LookupError(
            "Could not find these playlists were in "
            f"the database as given: {fmt_list(unfound_playlists)}"
            "so its ownership could not be updated. Aborting..."
        )


    # the 'data' field is a massive JSON file stored as a BLOB,
    # so it needs to be deserialized, so I can get to the correct field,
    # and then serialized again into bytes to be updated in the database
    for param_map, raw_json in zip(playlist_param_maps, all_pl_raw):

        parsed_json = json.loads(raw_json[1])

        parsed_json['OwnerUserId'] = user_id
        param_map['data_with_new_uid'] = json.dumps(parsed_json).encode('utf-8')

    cursor.executemany(
        """
        UPDATE TypedBaseItems
        SET data = :data_with_new_uid
        WHERE 
            type = 'MediaBrowser.Controller.Playlists.Playlist' 
            AND Name = :playlist_name
        """,
        playlist_param_maps
    )



def change_playist_owner_all(cursor: sqlite3.Cursor, user_id: str, all_user_ids: list[str], unowned_only: bool) -> list[str]:
    """
    Change the owner user all playlists in the database.

    :param cursor: Cursor object for database
    :type cursor: sqlite3.Cursor
    :param user_id: User ID, a lowercase UUID hexadecimal (without dashes)
    :type user_id: str
    :param all_user_ids: all user IDs for users on the server
    :type list[str]
    :param unowned_only: Whether to change playlist owners only for playlists that are not owned by any known user
    :type unowned_only: bool

    :return: List of all playlist names whose owner was changed.
    :rtype: list[str]
    """
    all_pl_rows = cursor.execute(
        """
        SELECT name, data 
        FROM TypedBaseItems 
        WHERE type = 'MediaBrowser.Controller.Playlists.Playlist' 
        """
    ).fetchall()


    # the 'data' field is a massive JSON file stored as a BLOB,
    # so it needs to be deserialized, so I can get to the correct field,
    # and then serialized again into bytes to be updated in the database
    param_maps = []
    for pl_row in all_pl_rows:
        
        parsed_json = json.loads(pl_row[1])  # raw binary JSON

        # pass over playlists that are owned by other known users
        if unowned_only and (parsed_json['OwnerUserId'] in all_user_ids):
            continue

        parsed_json['OwnerUserId'] = user_id

        param_maps.append(
            {
                'playlist_name': pl_row[0], 
                'data_with_new_uid': json.dumps(parsed_json).encode('utf-8')
            }
        )
        
    
    cursor.executemany(
        """
        UPDATE TypedBaseItems
        SET data = :data_with_new_uid
        WHERE 
            type = 'MediaBrowser.Controller.Playlists.Playlist' 
            AND Name = :playlist_name
        """,
        param_maps
    )

    return [ p_map['playlist_name'] for p_map in param_maps ]


def fetch_all_user_info(server_url: str) -> list[dict]:

    api_token = os.getenv("JELLYFIN_API_KEY")

    if not api_token:
        raise Exception(
            "API Key not found in environment (JELLYFIN_API_KEY)." + 
            "See setup instruction in repo README file on how to set" + 
            "one up."
            )
    
    curl = pycurl.Curl()
    curl.setopt(pycurl.HTTPHEADER, [f"Authorization: MediaBrowser Token={api_token}"])
    curl.setopt(pycurl.URL, f"{server_url}/Users")
    
    users_raw_str = curl.perform_rs()
    return json.loads(users_raw_str)


def get_user_id(user_info: list[dict], username: str) -> str:

    for user in user_info:
        if user['Name'] == username:
            return user['Id']
    
    raise Exception(f"User '{username}' not found on server.")


def get_all_user_ids(user_info: list[dict]) -> list[str]:
    
    user_ids = [user['Id'] for user in user_info]
    
    return user_ids


def get_default_db_path() -> str | None:
    """
    Searches the current system default locations for the Jellyfin Data directory, in the precedence given here: https://jellyfin.org/docs/general/administration/configuration#data-directory.

    Does not (currently) support Windows installations.
    
    :return: the filepath to the default Jellyfin Data Directory path with the highest precedence
    :rtype: str | None
    """
    xdg_home  = os.getenv("XDG_DATA_HOME")
    user_home = os.getenv("HOME")
    possible_data_paths = [
        os.getenv("JELLYFIN_DATA_DIR"),
        xdg_home  + "/jellyfin"              if xdg_home  else None,
        user_home + "/.local/share/jellyfin" if user_home else None
    ]

    # first non-null path
    for path in possible_data_paths:
        if path:
            return path + "/data/library.db"
        
    return None



def parse_args(program_args: list[str]) -> Namespace:
    pl_dir_opt = "--playlist-dir"
    
    ap = ArgumentParser(description="Changes the ownership of Jellyfin playlists.")

    ap.add_argument('-d','--database',
                    type=str,
                    default=get_default_db_path(),
                    required=False,
                    help="The path to the library.db SQLite database. Will try to" + 
                        "read from the default Jellyfin Data Directory if omitted." +
                        "see https://jellyfin.org/docs/general/administration/" +
                        "configuration/#data-directory for details."
                    )
    
    ap.add_argument('-s','--server-url',
                    type=str,
                    required=True,
                    help="The URL to your Jellyfin server."
                    )

    req_one_of = ap.add_mutually_exclusive_group(required=True)
    req_one_of.add_argument(
        '-p','--playlist',
        dest="playlists",
        help="The name of the playlist for which to change ownership " +
            "(case sensitive). This option can be repeated for multiple " +
            "playlists.",
        action="append"
        )
    
    req_one_of.add_argument(
        '--all-playlists',
        default=False,
        action='store_true',
        help="Change ownership of all the server's playlists, regardless of current" + 
            "owner, to the user specified by --user. Cannot be used with --playlist."
        )
    
    req_one_of.add_argument(
        '--all-unowned',
        default=False,
        action='store_true',
        help="Change ownership of all the server's playlists with an unknown " + 
            "owner ID to the user specified by --user. Cannot be used with --playlist."
        )
    
    # ap.add_argument('-l','--playlist-dir',
    #                 type=str,
    #                 required=False,
    #                 help="Change the user for every playlist in this "
    #                 )

    ap.add_argument('-u', '--user',
                    type=str,
                    required=True,
                    help="The user who will be the new owner of (all) the given playlist(s)." + 
                        "Only one user can be specified: to map different playlists to" + 
                        "different users, this program must be executed once for each" + 
                        "distinct user."
                    )

    # ap.add_argument('--lax',
    #                 default=False,
    #                 action='store_true',
    #                 required=False,
    #                 help="Only warn on failed playlist ownership change operation, instead of" + "
    #                     throw an error and crash."
    #                 )
    
    # ap.add_argument('-v', '--version', 
    #                 action="version", 
    #                 version=importlib.metadata.version('jellyfin-chown-pl'),
    #                 help="Print version and exit."
    #                 )
    
    ap.add_argument('--debug',
                    default=False,
                    action='store_true',
                    required=False,
                    help="This option lets the program crash fully, so a stack" + 
                        "trace will be printed to the console. Closes database " +
                        "connection if open."
                    )

    parsed_cli_args = ap.parse_args(program_args)

    # if there's STILL no database
    if not parsed_cli_args.database:
        raise FileNotFoundError(
            2, "Database not found",
            "Could not infer library database location from environment," + 
            "and no filepath to it was provided on the command line."
            )

    return parsed_cli_args



def main():

    cli_args = parse_args(sys.argv[1:])

    try:
        user_info = fetch_all_user_info(cli_args.server_url)
        user_id   = get_user_id(user_info, cli_args.user)
        all_ids   = get_all_user_ids(user_info)
    except Exception as e:

        if cli_args.debug:
            raise e
        
        print(f"{ERROR_RED}: Error fetching user ID:", 
              e, file=sys.stderr
              )
        sys.exit(1)

    try:
        if not os.path.exists(cli_args.database):
            raise FileNotFoundError(
                2, "Database not found",
                f"{cli_args.database} doesn't exist."
                )
        conn = sqlite3.connect(cli_args.database)

    except Exception as dbe:
        
        # just crash, hard
        if cli_args.debug:
            raise dbe
        
        print(f"{ERROR_RED}: The database could not be opened, "
              "due to the following error:", 
              dbe, file=sys.stderr
              )
        sys.exit(1)

    cursor = conn.cursor()

    try: 

        if cli_args.all_playlists or cli_args.all_unowned:

            # override playlist list with list of all playlists from database
            cli_args.playlists = change_playist_owner_all(cursor, user_id, all_ids, cli_args.all_unowned)

        elif len(cli_args.playlists) == 1:
            change_playist_owner_single(cursor, user_id, cli_args.playlists[0])

        else:
            change_playist_owner_many(
                cursor, 
                user_id, 
                cli_args.playlists
            )
        
    except Exception as e:
        
        # just crash, hard
        if cli_args.debug:
            conn.close()
            raise e
        
        pls_fmt_str = fmt_list(cli_args.playlists) if cli_args.playlists else "(all) "
        
        print(f"{ERROR_RED}: Playlist ownership could not be changed for "
            f"playlist set {pls_fmt_str}due to the following:\n\n", 
            e, file=sys.stderr
            )
        
        conn.close()
        sys.exit(1)

    conn.commit()
    conn.close()

    print(f"[\033[0;32m Ownership updated! \033[0m] "
          f"Updated to \033[1m{cli_args.user}\033[0m "
          f"for playlist set: {fmt_list(cli_args.playlists)}"
          )



if __name__ == "__main__":
    main()