FROM docker.io/python:3.10.14

LABEL MATAINER="Bruce Wu"

ADD dist/app/config-ops /opt/config-ops/
ADD dist/app/_internal/ /opt/config-ops/_internal/
ADD config.yaml.sample /opt/config-ops/config.yaml
ADD startup.sh /opt/config-ops/
RUN chmod 755 /opt/config-ops/startup.sh

WORKDIR /opt/config-ops/

ENTRYPOINT [ "./startup.sh" ]