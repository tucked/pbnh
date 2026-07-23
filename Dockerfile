FROM node:26-slim AS frontend
WORKDIR /frontend
COPY frontend/ ./
RUN npm ci && npm run build

FROM python:3.14-slim
# psycopg2: https://www.psycopg.org/docs/install.html#build-prerequisites
# python-magic: https://github.com/ahupp/python-magic#debianubuntu
RUN apt update && apt install --assume-yes \
    gcc python3-dev libpq-dev \
    libmagic1
RUN pip install --upgrade pip
RUN pip install --upgrade pipenv
WORKDIR /pbnh
COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy
COPY . .
COPY --from=frontend /frontend/dist/ pbnh/static/dist/
EXPOSE 8000
CMD ["pipenv", "run", "gunicorn", "pbnh:create_app(check_db=True)"]
