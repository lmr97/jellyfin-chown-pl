# Running this utility on Docker or Kubernetes

I published a Docker Hub image, [`lmr97/jellyfin-chown-pl`](https://hub.docker.com/r/lmr97/jellyfin-chown-pl), that has the Python program installed in it, as well as the following other utilities I find helpful for the task if I need to poke around the database and other files:

- `jq`, a command-line JSON parser 
- `xq`, an XML parser in the vein of `jq`
- `sqlite3`, a command-line client for a SQLite database
- `vim`, yes, I'm that kind of guy
- `less`, the classic Unix [terminal pager](https://en.wikipedia.org/wiki/Terminal_pager)