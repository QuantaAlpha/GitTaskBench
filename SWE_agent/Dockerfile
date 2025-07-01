FROM python:3.12

# Add Proxy settings
# ENV all_proxy=http://proxy.i.shaipower.com:3128
# ENV no_proxy=stepfun-inc.com,clear.ml,shaipower,shaipower.com,shaipower.local,shaipower.ml,basemind.com,brainpp.cn,kubebrain,kubebrain.com,127.0.0.1,10.0.0.0/8,localhost,svc
# ENV http_proxy=$all_proxy
# ENV https_proxy=$all_proxy

# ENV HTTP_PROXY=$all_proxy
# ENV HTTPS_PROXY=$all_proxy
# ENV NO_PROXY=$no_proxy

# RUN mkdir -p /etc/apt/sources.list.d && echo "deb http://mirrors.i.basemind.com/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list.d/basemind.list && echo "deb http://mirrors.i.basemind.com/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list.d/basemind.list && echo "deb http://mirrors.i.basemind.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list.d/basemind.list
# Set the working directory
WORKDIR /

# Configure apt to use the proxy
RUN echo 'Acquire::http::Proxy "${http_proxy}";' > /etc/apt/apt.conf.d/proxy.conf && \
    echo 'Acquire::https::Proxy "${https_proxy}";' >> /etc/apt/apt.conf.d/proxy.conf

# Install nodejs
RUN apt update && \
    apt install -y nodejs npm && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/apt/apt.conf.d/proxy.conf # Clean up apt proxy config

# Install git
RUN apt install -y git

# Install Docker CLI using the official Docker installation script
RUN curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh

# Copy the application code
# Do this last to take advantage of the docker layer mechanism
COPY . /

# Configure pip to use the proxy
RUN pip config set global.proxy $http_proxy

# Install Python dependencies
RUN pip install -e '.'

# Configure npm to use the proxy
RUN npm config set proxy $http_proxy && \
    npm config set https-proxy $https_proxy

# Install react dependencies ahead of time
# RUN cd sweagent/frontend && npm install

