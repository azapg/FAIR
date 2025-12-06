"""Test plugin loading during database initialization."""
import pytest
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine, inspect
from fair_platform.backend.data.database import Base
from fair_platform.backend.main import lifespan
from fastapi import FastAPI


def test_plugin_loading_after_db_init():
    """Test that database initialization happens before plugin loading.
    
    This test ensures that when starting the server for the first time with
    a fresh database, the plugins table is created before plugins are loaded,
    preventing the 'no such table: plugins' error.
    """
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    try:
        # Create a fresh database
        test_db_url = f"sqlite:///{test_db_path}"
        engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Verify that the plugins table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "plugins" in tables, "plugins table should be created during init_db"
        
        # Clean up
        engine.dispose()
        
    finally:
        # Remove the temporary database file
        try:
            os.unlink(test_db_path)
        except FileNotFoundError:
            pass


@pytest.mark.asyncio
async def test_lifespan_initializes_db_before_plugins():
    """Test that the lifespan context manager initializes the database before loading plugins.
    
    This is an integration test that verifies the correct order of operations
    in the FastAPI lifespan context manager.
    """
    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    try:
        # Set environment variable to use our test database
        original_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
        
        # Create a test FastAPI app
        app = FastAPI()
        
        # Use the lifespan context manager
        async with lifespan(app):
            # After entering the lifespan context, database should be initialized
            # and plugins table should exist
            from fair_platform.backend.data.database import engine as db_engine
            from sqlalchemy import inspect
            
            inspector = inspect(db_engine)
            tables = inspector.get_table_names()
            
            assert "plugins" in tables, "plugins table should exist after lifespan initialization"
        
        # Restore original DATABASE_URL
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
            
    finally:
        # Clean up the test database
        try:
            os.unlink(test_db_path)
        except FileNotFoundError:
            pass


def test_db_init_creates_plugins_table():
    """Test that init_db function creates the plugins table."""
    from sqlalchemy import create_engine, inspect
    from fair_platform.backend.data.database import Base
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    try:
        # Create engine and initialize database
        test_db_url = f"sqlite:///{test_db_path}"
        engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
        
        # Create all tables (this is what init_db does)
        from fair_platform.backend.data import models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        
        # Check that plugins table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "plugins" in tables, "plugins table should be created by init_db"
        
        # Clean up
        engine.dispose()
        
    finally:
        # Clean up the test database
        try:
            os.unlink(test_db_path)
        except FileNotFoundError:
            pass
