FROM docker.io/python:3.9.19

LABEL MATAINER="Bruce Wu"

ADD dist/app/config-ops /opt/config-ops/

ADD startup.sh /opt/config-ops/

ADD config.yaml.sample /optconfig-ops/config.yaml

ENTRYPOINT [ "/opt/config-ops/startup.sh" ]