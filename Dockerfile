# --- Stage 1: The "Builder" ---
# This stage's only job is to compile our C++ code into a .so file.
FROM gcc:12.3.0 AS builder

# --- FIX: Install cmake ---
# First, update the package lists, then install cmake.
# The '-y' flag automatically answers "yes" to any prompts.
RUN apt-get update && apt-get install -y cmake

WORKDIR /app
COPY ./engine /app/engine

# This command will now succeed because cmake is installed.
RUN cmake -S /app/engine -B /app/engine/build
RUN cmake --build /app/engine/build


# --- Stage 2: The "Final Image" ---
# This is the stage that will create our small, efficient final image.
FROM python:3.11-slim
WORKDIR /app

# --- FIX: Use modern ENV syntax ---
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the compiled C++ library from the "builder" stage.
COPY --from=builder /app/engine/build/libinsight.so /usr/local/lib/
# Update the linker cache so the system can find our .so file.
RUN ldconfig

# Copy the Python API code.
COPY ./api /app/api

# Expose the port the app runs on.
EXPOSE 8000

# The command to run when the container starts.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]