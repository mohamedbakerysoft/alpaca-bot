# Python Project Development Rules

## Code Style & Formatting

### PEP 8 Compliance
- Follow PEP 8 style guide strictly
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (Black formatter standard)
- Use snake_case for variables, functions, and module names
- Use PascalCase for class names
- Use UPPER_CASE for constants

### Import Organization
- Group imports in this order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library imports
- Use absolute imports when possible
- Avoid wildcard imports (`from module import *`)
- Sort imports alphabetically within each group

### Code Formatting
- Use Black formatter for consistent code formatting
- Use isort for import sorting
- Configure pre-commit hooks for automatic formatting

## Code Quality & Best Practices

### Type Hints
- Use type hints for all function parameters and return values
- Use `typing` module for complex types
- Use `Optional[Type]` for nullable parameters
- Use `Union[Type1, Type2]` for multiple possible types
- Use `List[Type]`, `Dict[Key, Value]` for collections

### Documentation
- Write docstrings for all public functions, classes, and modules
- Use Google-style or NumPy-style docstrings consistently
- Include parameter types, return types, and examples where helpful
- Document complex algorithms and business logic

### Error Handling
- Use specific exception types rather than generic `Exception`
- Create custom exceptions for domain-specific errors
- Use try-except blocks judiciously, not as control flow
- Always log exceptions with appropriate context
- Use `finally` blocks for cleanup when necessary

### Function Design
- Keep functions small and focused (single responsibility)
- Limit function parameters (max 5-7 parameters)
- Use keyword arguments for optional parameters
- Return early to reduce nesting
- Avoid deep nesting (max 3-4 levels)

### Class Design
- Use composition over inheritance when possible
- Implement `__str__` and `__repr__` methods for custom classes
- Use properties for computed attributes
- Follow SOLID principles
- Use dataclasses for simple data containers

## Testing

### Test Structure
- Use pytest as the testing framework
- Organize tests in a `tests/` directory mirroring the source structure
- Name test files with `test_` prefix
- Name test functions with `test_` prefix
- Use descriptive test names that explain what is being tested

### Test Quality
- Write unit tests for all public functions and methods
- Aim for 80%+ code coverage
- Use fixtures for test data and setup
- Mock external dependencies
- Test both happy path and edge cases
- Test error conditions and exception handling

### Test Organization
- Group related tests in test classes
- Use parametrized tests for testing multiple inputs
- Keep tests independent and isolated
- Use setup and teardown methods appropriately

## Project Structure

### Directory Layout
```
project_name/
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── main.py
│       ├── models/
│       ├── services/
│       ├── utils/
│       └── config/
├── tests/
├── docs/
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── .gitignore
├── README.md
├── pyproject.toml
└── setup.py
```

### Configuration Management
- Use environment variables for configuration
- Create separate config files for different environments
- Use `python-decouple` or similar for environment variable management
- Never commit secrets or sensitive data to version control
- Use `.env` files for local development (add to .gitignore)

## Dependencies & Environment

### Dependency Management
- Use `requirements.txt` or `pyproject.toml` for dependency specification
- Pin exact versions for production dependencies
- Separate development and production dependencies
- Regularly update dependencies and check for security vulnerabilities
- Use virtual environments for isolation

### Package Management
- Use pip-tools for dependency management
- Create `requirements.in` files and compile to `requirements.txt`
- Use `poetry` or `pipenv` for more advanced dependency management

## Security

### Input Validation
- Validate all user inputs
- Use parameterized queries for database operations
- Sanitize data before processing
- Use appropriate encoding/decoding

### Secrets Management
- Never hardcode secrets in source code
- Use environment variables or secret management services
- Rotate secrets regularly
- Use HTTPS for all external communications

## Performance

### Optimization Guidelines
- Profile before optimizing
- Use appropriate data structures for the use case
- Avoid premature optimization
- Use generators for large datasets
- Implement caching where appropriate
- Use async/await for I/O-bound operations

### Memory Management
- Be mindful of memory usage with large datasets
- Use context managers for resource management
- Close files, database connections, and other resources properly
- Use weak references when appropriate to avoid circular references

## Logging

### Logging Standards
- Use the `logging` module, not print statements
- Configure logging levels appropriately (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Include contextual information in log messages
- Use structured logging for production applications
- Rotate log files to prevent disk space issues

### Log Message Guidelines
- Write clear, actionable log messages
- Include relevant context (user ID, request ID, etc.)
- Use appropriate log levels
- Avoid logging sensitive information

## Git & Version Control

### Commit Guidelines
- Write clear, descriptive commit messages
- Use conventional commit format when possible
- Make atomic commits (one logical change per commit)
- Use feature branches for development
- Squash commits before merging to main

### Branch Strategy
- Use GitFlow or GitHub Flow branching strategy
- Protect main/master branch with required reviews
- Use descriptive branch names
- Delete merged branches

## Code Review

### Review Checklist
- Code follows style guidelines
- Functions are well-documented
- Tests are included and comprehensive
- No hardcoded secrets or sensitive data
- Error handling is appropriate
- Performance considerations are addressed
- Security best practices are followed

## Deployment

### Production Readiness
- Use environment-specific configuration
- Implement health checks
- Set up monitoring and alerting
- Use containerization (Docker) when appropriate
- Implement graceful shutdown handling
- Use process managers (systemd, supervisor) for service management

## AI Development Guidelines

### When Working with Trae AI
- Always follow these rules without asking for confirmation
- Prioritize code quality and maintainability
- Implement comprehensive error handling
- Write self-documenting code with clear variable names
- Include type hints and docstrings
- Create tests for new functionality
- Follow the established project structure
- Use context7 for all code implementations

### Code Generation Standards
- Generate production-ready code, not prototypes
- Include proper imports and dependencies
- Handle edge cases and error conditions
- Follow the project's existing patterns and conventions
- Ensure code is immediately runnable

---

**Note**: These rules should be followed consistently throughout the project. When in doubt, prioritize code readability, maintainability, and security.