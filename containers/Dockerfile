FROM python:3.13

RUN apt update

# Placing these on separate lines to take advantage of caching
# when I want to add new utilities
RUN apt install -y less 
RUN apt install -y vim 
RUN apt install -y jq 
RUN apt install -y xq 
RUN apt install -y sqlite3

COPY ./ /jellyfin-chown-pl
RUN pip install /jellyfin-chown-pl

CMD [ "sleep", "infinity" ]