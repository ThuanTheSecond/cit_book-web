# ARG PYTHON_VERSION=3.13-slim

# FROM python:${PYTHON_VERSION}

# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # install psycopg2 dependencies.
# RUN apt-get update && apt-get install -y \
#     libpq-dev \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# RUN mkdir -p /code

# WORKDIR /code

# COPY requirements.txt /tmp/requirements.txt
# RUN set -ex && \
#     pip install --upgrade pip && \
#     pip install -r /tmp/requirements.txt && \
#     rm -rf /root/.cache/
# COPY . /code

# ENV SECRET_KEY "6RwgocRwBXoo0K7WNoZlgTR6nMB8Ozu9iJDzGLE7neTgyvNuVu"
# RUN python manage.py collectstatic --noinput

# EXPOSE 8000

# CMD ["gunicorn","--bind",":8000","--workers","2","book_cit_web.wsgi"]
# Dockerfile
# Dockerfile
FROM python:3.11-slim

# Ngăn Python tạo .pyc và buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Thư mục làm việc
WORKDIR /app

# Cài đặt OS deps cần cho psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Cài dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy toàn bộ code
COPY . .

# Đảm bảo entrypoint có quyền chạy
RUN chmod +x ./entrypoint.sh

# Command mặc định chạy Gunicorn
CMD ["gunicorn", "book_cit_web.wsgi:application", "--bind", "0.0.0.0:$PORT", "--workers", "3", "--log-file", "-"]
