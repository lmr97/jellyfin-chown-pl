# Running this utility on Docker or Kubernetes

**This guide is for those use container-runtime-managed volumes** for their Jellyfin setup. If you're using a Docker bind mount or a Kubernetes volume with a `local-storage` class, just run the program outside a container on the local files.

## Docker image

I published a Docker Hub image, [`lmr97/jellyfin-chown-pl`](https://hub.docker.com/r/lmr97/jellyfin-chown-pl), that has the Python program installed in it, as well as the following other utilities I find helpful for the task if I need to poke around the database and other files:

- `jq`, a command-line JSON parser 
- `xq`, an XML parser in the vein of `jq`
- `sqlite3`, a command-line client for a SQLite database
- `vim`, yes, I'm that guy
- `less`, the classic Unix [terminal pager](https://en.wikipedia.org/wiki/Terminal_pager)

## Runing on Docker

To run the program inside the container, all you need to do is mount the volume or directory where you have your Jellyfin data directory, and specify the command line arguments: 

Say you have a Docker volume `jellyfin_data_dir` where you keep your Jellyfin data directory, and your Jellyfin instance was running in a container named `jellyfin-svr` listening on port 8096, and you wanted to transfer all your playlists' owners to emma. Note that `jellyfin_data_dir` needs to be The command to do so would look like this:

```
docker run \
    --name jf-chown-pl \
    --rm \                             # delete container when execution completes
    --env JELLYFIN_API_KEY=deadbeefdeadbeefdeadbeefdeafbead \
    --volume jellyfin_data_dir:/datadir \
    lmr97/jellyfin-chown-pl:latest \
    jfchownpl \
        --server-url jellyfin-svr:8096  # Docker containers share the same network by default, with hostnames set to the container name
        --database /datadir/data/library.db \  # path relative to *container's* root directory
        --user emma
        --all-playlists
```

The default command for the image is simply `sleep infinity`, so you can also spin up a container and open up a shell inside it with `docker exec`:

```
# this first command is just like the one above, prior to the jfchownpl CMD
docker run \
    --name jf-chown-pl \
    --env JELLYFIN_API_KEY=deadbeefdeadbeefdeadbeefdeafbead \
    --volume jellyfin_data_dir:/datadir \
    lmr97/jellyfin-chown-pl:latest
docker exec -it jf-chown-pl bash
```

### Docker Compose

Included in this directory is a template Docker Compose file, `compose.yaml`, that does the same thing as the commands above, except with the data directory given as an environment variable instead of a command-line argument to `jfchownpl`.


## Kubernetes

See the `k8s-jfchownpl.yaml` for an example Deployment.  You'll need to make sure that the access mode of the volume where you keep your Jellyfin data directory is `ReadWriteMany`, so it can be mounted in the `jfchownpl` Pod alongside your Jellyfin server Pod. Otherwise, you'll need to delete the running Jellyfin server Pod so you can edit the database file (`library.db`). The Jellyfin server pod itself is stateless, so this shouldn't cause issues.

As a personal note: I run Jellyfin out of a Kubernetes cluster (a k3s cluster specifically), and I tested this, and it worked out okay.