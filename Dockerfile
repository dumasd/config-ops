FROM docker.io/python:3.10.14

LABEL MATAINER="Bruce Wu"

WORKDIR /opt/config-ops/

ADD configops/ ./configops/
ADD requirements.txt ./requirements.txt
ADD config.yaml.sample ./config.yaml

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "-m", "flask", "--app", "configops/app.py", "run"]