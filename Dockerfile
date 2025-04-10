FROM docker.io/python:3.10.14

LABEL MATAINER="Bruce Wu"

WORKDIR /opt/config-ops/

COPY configops/ ./configops/
COPY requirements.txt ./requirements.txt
COPY config.yaml.sample ./config.yaml

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python3", "-m", "flask", "--app", "configops/app.py", "run"]