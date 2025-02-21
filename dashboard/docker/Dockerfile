FROM python:3.12-slim

RUN apt update
RUN apt install -y nano

COPY requirements.txt .
RUN pip3 install -r requirements.txt

CMD [ "gunicorn","--chdir=/workdir/dashboard/",  "--workers=1", "--threads=1", "-b 0.0.0.0:80","dashboard:server"]
