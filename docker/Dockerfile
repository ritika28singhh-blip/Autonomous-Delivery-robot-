FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    QT_QPA_PLATFORM=xcb \
    DISPLAY=:99

# System libs CoppeliaSim (Qt5-based) needs at runtime, plus Xvfb for a
# headless virtual display and Python for the control scripts.
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11-utils x11vnc novnc websockify \
    python3 python3-pip python3-venv \
    libgl1 libglu1-mesa libglib2.0-0 \
    libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-sync1 \
    libxcb-xfixes0 libxcb-xkb1 libxkbcommon0 libxkbcommon-x11-0 \
    libxrandr2 libxcursor1 libxi6 libxtst6 libxcomposite1 libxdamage1 \
    libnss3 libfontconfig1 libdbus-1-3 libasound2 libgtk-3-0 \
    ffmpeg wget xz-utils \
    && rm -rf /var/lib/apt/lists/*

ARG COPPELIASIM_VERSION=V4_6_0_rev18
ARG COPPELIASIM_ARCHIVE=CoppeliaSim_Edu_V4_6_0_rev18_Ubuntu22_04
WORKDIR /opt
RUN wget -q "https://downloads.coppeliarobotics.com/${COPPELIASIM_VERSION}/${COPPELIASIM_ARCHIVE}.tar.xz" -O CoppeliaSim.tar.xz && \
    tar xf CoppeliaSim.tar.xz -C /opt && \
    mv "/opt/${COPPELIASIM_ARCHIVE}" /opt/coppeliasim && \
    rm CoppeliaSim.tar.xz

ENV COPPELIASIM_ROOT=/opt/coppeliasim \
    LD_LIBRARY_PATH=/opt/coppeliasim:${LD_LIBRARY_PATH} \
    PATH=/opt/coppeliasim:${PATH}

RUN pip3 install --no-cache-dir \
    coppeliasim-zmqremoteapi-client \
    pyzmq \
    numpy \
    opencv-python-headless

WORKDIR /workspace
CMD ["/bin/bash"]
