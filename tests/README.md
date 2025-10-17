# LG-Urban Test Suite

This directory contains comprehensive tests for the LG-Urban application, covering unit tests, integration tests, and end-to-end tests.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── run_tests.py             # Test runner script
├── requirements.txt         # Test dependencies
├── unit/                    # Unit tests
│   ├── test_artifact_storage.py    # Artifact storage tests
│   └── test_database_operations.py # Database operation tests
├── integration/             # Integration tests
│   └── test_sandbox_execution.py   # Sandbox execution tests
└── e2e/                     # End-to-end tests
    └── test_full_workflow.py       # Complete workflow tests
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r tests/requirements.txt
```

### Quick Start

Run all tests:
```bash
python tests/run_tests.py all
```

Run specific test categories:
```bash
python tests/run_tests.py unit
python tests/run_tests.py integration  
python tests/run_tests.py e2e
```

### Advanced Options

Verbose output:
```bash
python tests/run_tests.py all --verbose
```

With coverage reporting:
```bash
python tests/run_tests.py all --coverage
```

### Direct pytest Usage

You can also run tests directly with pytest:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_artifact_storage.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

## Test Categories

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation

**Coverage**:
- Artifact storage operations (deduplication, file operations)
- Database operations (constraints, cascade deletes, relationships)
- Data validation and integrity

**Key Tests**:
- `test_artifact_storage.py`: SHA-256 deduplication, blob operations
- `test_database_operations.py`: Cascade deletes, unique constraints

### Integration Tests (`tests/integration/`)

**Purpose**: Test component interactions without full system

**Coverage**:
- Sandbox code execution
- Session management
- Artifact creation and ingestion
- Error handling and timeouts

**Key Tests**:
- `test_sandbox_execution.py`: Code execution, variable persistence, artifact creation

### End-to-End Tests (`tests/e2e/`)

**Purpose**: Test complete user workflows

**Coverage**:
- Full API workflows
- Thread creation and message handling
- Artifact display and download
- Error handling across the system

**Key Tests**:
- `test_full_workflow.py`: Complete user journeys, API endpoints

## Test Data

Tests use:
- **In-memory SQLite** for fast database tests
- **Temporary directories** for blobstore testing
- **Mocked services** for external dependencies (Docker, OpenAI)
- **Isolated test data** that doesn't affect production

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -r tests/requirements.txt
    python tests/run_tests.py all --coverage
```

## Debugging Tests

### Running Individual Tests

```bash
# Run specific test function
pytest tests/unit/test_artifact_storage.py::TestBlobstoreOperations::test_ensure_blobstore_creation

# Run with debug output
pytest tests/unit/test_artifact_storage.py -v -s
```

### Test Database Inspection

For database-related tests, you can inspect the test database:

```python
# In test code
async def test_something(db_session):
    # Add debug prints
    result = await db_session.execute("SELECT * FROM threads")
    print(result.fetchall())
```

## Coverage Goals

- **Unit Tests**: 90%+ coverage of core business logic
- **Integration Tests**: Cover all major component interactions  
- **E2E Tests**: Cover all critical user workflows

## Adding New Tests

1. **Unit Tests**: Add to `tests/unit/` for isolated component testing
2. **Integration Tests**: Add to `tests/integration/` for component interaction testing
3. **E2E Tests**: Add to `tests/e2e/` for complete workflow testing

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<FeatureName>`
- Test methods: `test_<specific_behavior>`

### Example Test Structure

```python
class TestNewFeature:
    """Test new feature functionality."""
    
    @pytest.mark.asyncio
    async def test_specific_behavior(self, db_session, test_thread):
        """Test specific behavior with given inputs."""
        # Arrange
        # Act  
        # Assert
        pass
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the project root
2. **Database Errors**: Check that test database is properly configured
3. **Mock Issues**: Verify mock setup matches actual service interfaces
4. **Timeout Issues**: Increase timeout values for slow operations

### Getting Help

- Check test output for specific error messages
- Use `pytest -v` for verbose output
- Add debug prints in test code
- Check that all dependencies are installed
