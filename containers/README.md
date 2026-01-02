# Running this utility on Docker or Kubernetes

**This guide is for those keeping their Jellyfin data directory in a container-runtime-managed volume**. If you're using a Docker bind mount or a , just run the program locally.

## Docker image

I published a Docker Hub image, [`lmr97/jellyfin-chown-pl`](https://hub.docker.com/r/lmr97/jellyfin-chown-pl), that has the Python program installed in it, as well as the following other utilities I find helpful for the task if I need to poke around the database and other files:

- `jq`, a command-line JSON parser 
- `xq`, an XML parser in the vein of `jq`
- `sqlite3`, a command-line client for a SQLite database
- `vim`, yes, I'm that kind of guy
- `less`, the classic Unix [terminal pager](https://en.wikipedia.org/wiki/Terminal_pager)

## Runing on Docker

To run the program inside the container, all you need to do is mount the volume or directory where you have your Jellyfin data directory, and specify the command line arguments: 

Say you bind-mounted a your `~/.local/share/jellyfin` directory into your Jellyfin container, at `/datadir` in the container, and you wanted to transfer all your playlists' owners to emma. The command to do so would look like this:

```
docker run \
    --name jf-chown-pl \
    --rm \                          # delete container when execution completes
    --env JELLYFIN_API_KEY=deadbeefdeadbeefdeadbeefdeafbead \
    --mount type=bind,src="~/.local/share/jellyfin",dst=/datadir \
    lmr97/jellyfin-chown-pl:latest \
    jfchownpl \
        --database /datadir/data/library.db \
        --user emma
        --all-playlists
```

The default command for the image is simply `sleep infinity`, so you can also spin up a container and get into it with `docker exec`:

```
docker run \
    --name jf-chown-pl \
    --env JELLYFIN_API_KEY=deadbeefdeadbeefdeadbeefdeafbead \
    --mount type=bind,src="~/.local/share/jellyfin",dst=/datadir \
    lmr97/jellyfin-chown-pl:latest
docker exec -it jf-chown-pl bash
```