FROM ubuntu:20.04
LABEL maintainer="UNAVCO"

RUN apt-get update && \
    apt-get install -y gfortran python3-pip unzip wget && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/gnssrefl/exe /etc/gnssrefl/orbits /etc/gnssrefl/refl_code/Files

RUN cd /tmp && \
    wget https://www.unavco.org/software/data-processing/teqc/development/teqc_CentOSLx86_64d.zip \
    && unzip teqc_CentOSLx86_64d.zip -d /etc/gnssrefl/exe \
    && rm teqc*

COPY vendor/gfzrnx_1.15-8044_lx64 /etc/gnssrefl/exe/gfzrnx
COPY vendor/CRX2RNX /etc/gnssrefl/exe/CRX2RNX

ENV EXE=/etc/gnssrefl/exe
ENV ORBITS=/etc/gnssrefl/orbits
ENV REFL_CODE=/etc/gnssrefl/refl_code

ENV PATH="/etc/gnssrefl/exe:$PATH"

COPY pyproject.toml README.md setup.py /usr/src/gnssrefl/
COPY gnssrefl /usr/src/gnssrefl/gnssrefl
RUN pip3 install /usr/src/gnssrefl
