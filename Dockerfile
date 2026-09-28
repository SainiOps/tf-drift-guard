FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip git \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform CLI (needed for drift check)
ARG TF_VERSION=1.9.5
RUN curl -sSLo /tmp/terraform.zip https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && rm /tmp/terraform.zip

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scan.py .

ENTRYPOINT ["python", "/app/scan.py"]
