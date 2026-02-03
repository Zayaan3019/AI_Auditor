# Contributing to AI Auditor

Thank you for your interest in contributing to AI Auditor! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Keep discussions professional

## Getting Started

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/ai-auditor.git
   cd ai-auditor
   ```

2. **Set up development environment**
   ```bash
   poetry install --with dev
   cp .env.example .env
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Before Making Changes

1. Ensure all tests pass:
   ```bash
   make test
   ```

2. Ensure code is formatted:
   ```bash
   make format
   ```

### Making Changes

1. Write clean, readable code following project conventions
2. Add docstrings to all functions and classes
3. Follow PEP 8 style guidelines
4. Use type hints where appropriate

### Testing

1. Write tests for new features:
   ```python
   # tests/test_your_feature.py
   import pytest
   
   def test_your_feature():
       # Arrange
       # Act
       # Assert
       pass
   ```

2. Run tests locally:
   ```bash
   make test
   ```

3. Ensure coverage doesn't decrease

### Committing Changes

1. Use clear, descriptive commit messages:
   ```
   feat: Add reranking support for RAG engine
   
   - Implement cross-encoder reranking
   - Add configuration options
   - Update documentation
   ```

2. Commit message prefixes:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Test changes
   - `refactor:` Code refactoring
   - `perf:` Performance improvements
   - `chore:` Maintenance tasks

### Pull Requests

1. **Before submitting:**
   - Run all checks: `make check`
   - Update CHANGELOG.md
   - Update documentation if needed

2. **PR Description should include:**
   - What changes were made
   - Why these changes were needed
   - How to test the changes
   - Screenshots (if UI changes)
   - Related issues

3. **PR Template:**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   How were these changes tested?
   
   ## Checklist
   - [ ] Tests pass locally
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated
   ```

## Code Style

### Python Style
- Follow PEP 8
- Use Black for formatting (120 char line length)
- Use isort for import sorting
- Use type hints

### Example:
```python
from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger


class MyClass:
    """Brief description of the class.
    
    More detailed description if needed.
    
    Args:
        param1: Description of param1.
        param2: Description of param2.
    """
    
    def __init__(self, param1: str, param2: int = 0) -> None:
        self.param1 = param1
        self.param2 = param2
    
    async def my_method(self, input_data: Dict[str, Any]) -> List[str]:
        """Brief description of method.
        
        Args:
            input_data: Description of input.
            
        Returns:
            Description of return value.
            
        Raises:
            ValueError: When input is invalid.
        """
        if not input_data:
            raise ValueError("input_data cannot be empty")
        
        # Implementation
        result = []
        return result
```

## Testing Guidelines

### Unit Tests
- Test individual functions/methods
- Mock external dependencies
- Use fixtures for common setup

### Integration Tests
- Test API endpoints
- Test component interactions
- Use TestClient for FastAPI

### Test Structure
```python
@pytest.mark.asyncio
async def test_feature_success():
    """Test feature works correctly."""
    # Arrange - Set up test data
    test_input = "test"
    
    # Act - Execute the code
    result = await my_function(test_input)
    
    # Assert - Verify results
    assert result == expected_output
```

## Documentation

### Docstrings
- Use Google style docstrings
- Include types in Args and Returns
- Document exceptions

### README Updates
- Update when adding new features
- Keep examples current
- Update configuration documentation

## Security

### Reporting Vulnerabilities
- **DO NOT** open public issues for security vulnerabilities
- Email security concerns to: security@example.com
- Include detailed description and reproduction steps

### Security Guidelines
- Never commit secrets or API keys
- Use environment variables for sensitive data
- Validate all user inputs
- Follow OWASP guidelines

## Performance

### Performance Guidelines
- Use async/await for I/O operations
- Minimize database queries
- Use caching where appropriate
- Profile before optimizing

### Benchmarking
```bash
make benchmark
```

## Review Process

1. **Automated Checks**
   - All CI/CD checks must pass
   - Code coverage must not decrease
   - No security vulnerabilities

2. **Code Review**
   - At least one approval required
   - Address all review comments
   - Keep PRs focused and small

3. **Merging**
   - Squash and merge for feature PRs
   - Update CHANGELOG.md
   - Tag releases following semantic versioning

## Release Process

1. Update version in pyproject.toml
2. Update CHANGELOG.md
3. Create release branch
4. Tag release: `git tag v0.2.0`
5. Push tags: `git push --tags`
6. Create GitHub release
7. Deploy to production

## Questions?

- Open a discussion on GitHub
- Check existing issues and PRs
- Read the documentation

Thank you for contributing! 🎉
