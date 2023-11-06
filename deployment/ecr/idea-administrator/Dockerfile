FROM public.ecr.aws/docker/library/python:3.9.16-slim

WORKDIR /root

RUN apt-get update && \
    apt-get -y install \
    curl \
    tar \
    unzip \
    locales \
    && apt-get clean


ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL="en_US.UTF-8" \
    LC_CTYPE="en_US.UTF-8" \
    LANG="en_US.UTF-8"

RUN sed -i -e "s/# $LANG.*/$LANG UTF-8/" /etc/locale.gen \
    && locale-gen "en_US.UTF-8" \
    && dpkg-reconfigure locales

# install aws cli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip -qq awscliv2.zip && \
    ./aws/install && \
    rm -rf ./aws awscliv2.zip

# install nvm and node
RUN set -uex && \
    apt-get update && \
    apt-get install -y ca-certificates curl gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    NODE_MAJOR=18 && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
	apt-get install nodejs -y

# add all packaged artifacts to container
ARG PUBLIC_ECR_TAG
ENV PUBLIC_ECR_TAG=${PUBLIC_ECR_TAG}
ADD all-*.tar.gz cfn_params_2_values.sh /root/.idea/downloads/

# install administrator app
RUN mkdir -p /root/.idea/downloads/idea-administrator-${PUBLIC_ECR_TAG} && \
    tar -xvf /root/.idea/downloads/idea-administrator-*.tar.gz -C /root/.idea/downloads/idea-administrator-${PUBLIC_ECR_TAG} && \
    /bin/bash /root/.idea/downloads/idea-administrator-${PUBLIC_ECR_TAG}/install.sh && \
    rm -rf /root/.idea/downloads/idea-administrator-${PUBLIC_ECR_TAG}

CMD ["bash"]


