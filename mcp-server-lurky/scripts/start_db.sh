#!/bin/bash
# Start PostgreSQL for Lurky API caching
# This starts a local PostgreSQL container for caching Twitter Space summaries.

set -e  # Exit on error

CONTAINER_NAME="lurky-cache-postgres"
DB_NAME="lurky_db"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_PORT="5432"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if port 5432 is already in use by another container
PORT_IN_USE=$(docker ps --format "{{.Names}}" --filter "publish=5432" | grep -v "^$" || true)
if [ -n "$PORT_IN_USE" ] && [ "$PORT_IN_USE" != "$CONTAINER_NAME" ]; then
    echo "Found existing container on port 5432: $PORT_IN_USE"
    echo "Validating that it is a PostgreSQL container..."
    
    # Validate it's actually PostgreSQL by checking for pg_isready
    if ! docker exec "$PORT_IN_USE" pg_isready -U postgres &> /dev/null; then
        echo "Error: Container $PORT_IN_USE on port 5432 is not a PostgreSQL container or is not ready."
        echo "Please stop the container or use a different port."
        exit 1
    fi
    
    echo "✓ Verified PostgreSQL container is ready."
    echo "Using existing PostgreSQL container instead of creating a new one."
    echo ""
    
    # Check if the database exists
    DB_EXISTS=$(docker exec "$PORT_IN_USE" psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "")
    
    if [ "$DB_EXISTS" = "1" ]; then
        echo "✓ Database '$DB_NAME' already exists."
    else
        echo "Creating database '$DB_NAME' in existing container..."
        docker exec "$PORT_IN_USE" psql -U postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Database may already exist or creation failed."
    fi
    
    # Check if user exists and has privileges
    USER_EXISTS=$(docker exec "$PORT_IN_USE" psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null || echo "")
    if [ "$USER_EXISTS" = "1" ]; then
        echo "✓ User '$DB_USER' already exists."
        # Ensure privileges are granted
        docker exec "$PORT_IN_USE" psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
    else
        echo "Creating user '$DB_USER'..."
        docker exec "$PORT_IN_USE" psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "User creation skipped (may already exist)."
        docker exec "$PORT_IN_USE" psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
    fi
    
    echo ""
    echo "Using existing PostgreSQL container: $PORT_IN_USE"
    echo "Connection: postgresql://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME"
    echo ""
    exit 0
fi

# Check if container exists
if ! docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Creating Lurky Cache PostgreSQL container on port $DB_PORT..."
    docker run -d \
      --name "$CONTAINER_NAME" \
      -e POSTGRES_PASSWORD="$DB_PASSWORD" \
      -e POSTGRES_DB="$DB_NAME" \
      -e POSTGRES_USER="$DB_USER" \
      -v lurky-cache-postgres-data:/var/lib/postgresql \
      -p "$DB_PORT:5432" \
      postgres:16
    echo "Container created. Waiting for PostgreSQL to initialize..."
    sleep 10
else
    # Check if container is already running
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo "Lurky Cache PostgreSQL container is already running."
    else
        echo "Starting existing Lurky Cache PostgreSQL container..."
        docker start "$CONTAINER_NAME"
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
    fi
fi

# Wait for PostgreSQL to be ready
echo "Checking PostgreSQL readiness..."
for i in {1..30}; do
    if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" &> /dev/null; then
        echo "PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Warning: PostgreSQL did not become ready within 30 seconds."
        exit 1
    fi
    sleep 1
done

echo ""
echo "PostgreSQL is running!"
echo "Container: $CONTAINER_NAME"
echo "Connection: postgresql://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME"
echo ""
echo "To stop the database:"
echo "  docker stop $CONTAINER_NAME"
echo ""
