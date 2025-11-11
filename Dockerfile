# Use Python slim image
FROM python:3.13

# Set work directory
WORKDIR /project

# Install Poetry
RUN pip install --upgrade pip && pip install poetry

# Configure Poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Copy Poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies without installing the project itself
RUN poetry install --no-root

# Copy all project files
COPY . .

# Run the application
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]