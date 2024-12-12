FROM public.ecr.aws/amazonlinux/amazonlinux:2023

ENV DEBIAN_FRONTEND=noninteractive

# add all packaged artifacts to container
ARG PUBLIC_ECR_TAG
ENV PUBLIC_ECR_TAG=${PUBLIC_ECR_TAG}
ADD all-*.tar.gz python.sh /opt/res/downloads/

# install Python 3.9.16 which is required to run RES applications
RUN yum install -y wget openssl openssl-devel tar gzip gcc zlib-devel
RUN . /opt/res/downloads/python.sh

# install SSSD dependencies
RUN yum install -y sssd-ldap sssd-krb5 sssd-tools

ENV PATH="/opt/res/python/latest/bin:${PATH}"

# install ad-sync app
RUN yum install -y openldap-devel
RUN mkdir -p /opt/res/downloads/ad-sync-${PUBLIC_ECR_TAG} && \
    tar -xvf /opt/res/downloads/ad-sync-*.tar.gz -C /opt/res/downloads/ad-sync-${PUBLIC_ECR_TAG} && \
    res_python -m venv venv && \
    source venv/bin/activate && \
    python -m pip install --upgrade pip==23.2.1 && \
    pip install -r /opt/res/downloads/ad-sync-${PUBLIC_ECR_TAG}/requirements.txt && \
    pip install $(ls /opt/res/downloads/ad-sync-${PUBLIC_ECR_TAG}/*-lib.tar.gz) && \
    rm -rf /opt/res/downloads/ad-sync-${PUBLIC_ECR_TAG}
