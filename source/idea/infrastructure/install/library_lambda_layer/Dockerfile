FROM public.ecr.aws/amazonlinux/amazonlinux:2023

ARG LIBRARY_TAR_FILE=${LIBRARY_TAR_FILE}
ARG LIBRARY_REQUIREMENTS_FILE=${LIBRARY_REQUIREMENTS_FILE}

# https://github.com/pyenv/pyenv?tab=readme-ov-file#installation
# https://github.com/pyenv/pyenv/wiki#suggested-build-environment
RUN yum install -y gcc make patch zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel
RUN yum install -y git tar
ENV HOME="/root"

RUN cd ${HOME}
COPY ${LIBRARY_REQUIREMENTS_FILE} .
COPY ${LIBRARY_TAR_FILE} .

RUN git clone https://github.com/pyenv/pyenv.git ${HOME}/.pyenv
RUN cd ${HOME}/.pyenv && src/configure && make -C src

ENV PYENV_ROOT="${HOME}/.pyenv"
ENV PATH="${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}"

# Python path for lambda layer as specified in the docs
# https://docs.aws.amazon.com/lambda/latest/dg/python-layers.html#python-layer-paths
RUN mkdir -p /asset/python

RUN cd ${HOME}

ENV PYTHON_VERSION=3.9
RUN pyenv install ${PYTHON_VERSION}
RUN pyenv global ${PYTHON_VERSION}

RUN pip install -r ${LIBRARY_REQUIREMENTS_FILE} --prefix=/asset/python
RUN pip install ${LIBRARY_TAR_FILE} --prefix=/asset/python
RUN rm -rf /asset/python/bin || true

ENV PYTHON_VERSION=3.11
RUN pyenv install ${PYTHON_VERSION}
RUN pyenv global ${PYTHON_VERSION}

RUN pip install -r ${LIBRARY_REQUIREMENTS_FILE} --prefix=/asset/python
RUN pip install ${LIBRARY_TAR_FILE} --prefix=/asset/python
RUN rm -rf /asset/python/bin || true

ENV PYTHON_VERSION=3.12
RUN pyenv install ${PYTHON_VERSION}
RUN pyenv global ${PYTHON_VERSION}

RUN pip install -r ${LIBRARY_REQUIREMENTS_FILE} --prefix=/asset/python
RUN pip install ${LIBRARY_TAR_FILE} --prefix=/asset/python
RUN rm -rf /asset/python/bin || true
