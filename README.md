# Transfer ownership for Jellyfin playlists

**For Jellyfin <= 10.10.7**

This is a small utility that fixes the issue where playlists cannot be edited, when loaded automatically from XML files gerea. This happens because the Jellyfin Server sets the `OwnerUserId` value to the nil UUID (`00000000000000000000000000000000`), which means it not owned by anyone, so it exists as read-only to all users (even administrators).

## Why doesn't editing the XML playlist files work?

You would think that a simple change in the XML files that (seem to) define playlists would be sufficient. But no! The value in that file is *overwriten* by a value in the SQLite database `library.db` (in `<Jellyfin data directory>/data/` on Unix-like deployments) upon a library rescan. 

## So I can just update the database and that will do it?

Sort of. Pretty much all the data and metadata (sans the actual audio and video files) is in the TypedBaseItems table of the Library database. This table includes the information on essentially every piece of media in your library, and it has a column called OwnerID. So updating this field for the desired playlist object would change the ownership, right?

Wrong again! The *real* ownership value is buried in a massive JSON file, converted to a BLOB, in the `data` field of that table (yes, the column is literally just called "data") on a given playlist's row. So here's what you would need to do to change the ownership of a playlist named `CoolSongs` to a user `emma`:

1. Query the database for the `data` field of the row with `name = 'CoolSongs'`

2. Copy out this text to somewhere you can edit it (the SQLite client typically converts it to text for you from the raw BLOB)

3. Open a browser and go to your administrator Dashboard > Users > emma 

4. Look in the URL on the emma's page, and find the field of the query string `userId`, and copy that value. I'll call this value `$USERID`

5. Go back to your JSON file/text/object, and replace the `OwnerUserId` value in the JSON with the `$USERID`

6. Render the JSON file as an ASCII hexdump, and store that somewhere

7. Update the `data` field for `CoolSongs` using SQLite's [BLOB literal syntax](https://www.sqlite.org/lang_expr.html#literal_values_constants_) (`X'<hex ASXII text>'`)

But that's kind of a pain, isn't it? That's why this program exists, to streamline this hassle. 

## Why can't I use the API? Wouldn't that be simpler?

It would be &mdash; if it worked. API tokens will not work with the `/Playlists` endpoint ([open issue](https://github.com/jellyfin/jellyfin/issues/12999), [discussion](https://github.com/orgs/jellyfin/discussions/12868)), and from my experience, simply using the browser session token gives exactly the same error (a 403 Forbidden error from the server).

You can even see in the source code that all the server does is check if `OwnerUserId == UserId`, and checks if the user is in the playlist's shares, and neglects the case where the `OwnerUserId` is simply a nil UUID ([source](https://github.com/jellyfin/jellyfin/blob/d28ee6d71415b4c1f5c158f30f427b6952b8d65b/Jellyfin.Api/Controllers/PlaylistsController.cs#L132)).

## Will I always have to use this script to fix this issue?

Hopefully not! I want to work on a PR that fixes this issue at at the source, by taking all `playlist.xml` files found on the first library scan of a new installation, and assigning their ownership to the administrator if the `OwnerUserID` in the file does not belong to a known user. This will at least let someone edit the playlists.


# Installation

## Pre-install setup

1. Open your browser and navigate to your administrator Dashboard

2. Go to the API Keys section and create a new API key.

3. Add this key to your shell environment as `JELLYFIN_API_KEY`:

    ```
    export JELLYFIN_API_KEY=<your key goes here>
    ```

This project is structured as a Python library, so it can be installed with `pip` or `pipx`, or `uv`. Each of these provide the CLI program `jfchownpl` (see [Usage](#Usage) section below). Poetry is also supported. 

Here's the installation for each of the tools:

## `pip` / `pipx`

(I'm using `pipx` below, but the commands are identical with `pip`)

```
git clone https://github.com/lmr97/jellyfin_chown_pl.git
pipx install ./jellyfin_chown_pl
```

## `uv`

```
git clone https://github.com/lmr97/jellyfin_chown_pl.git
uv tool install ./jellyfin_chown_pl
```


# Usage

