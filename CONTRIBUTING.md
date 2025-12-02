# Contributing to VoceVibe

Thank you for your interest in contributing to VoceVibe! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. Check if the issue already exists in the GitHub Issues
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)

### Submitting Changes

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed
4. **Test your changes**
   - Ensure the application runs without errors
   - Test on macOS with Apple Silicon
5. **Commit your changes**
   ```bash
   git commit -m "Add: description of your changes"
   ```
6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Create a Pull Request**
   - Provide a clear description of changes
   - Reference any related issues

## Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for functions and classes

### Testing
- Test audio input/output functionality
- Verify STT accuracy with both English and French
- Check OSC communication if modifying that component

### Documentation
- Update README.md if adding new features
- Update DEVELOPMENT_HISTORY.md for significant changes
- Add inline comments for complex algorithms

## Areas for Contribution

- Audio processing improvements
- STT accuracy enhancements
- UI/UX improvements
- Documentation improvements
- Performance optimizations
- Cross-platform support (if applicable)

## Questions?

Feel free to open an issue for questions or discussions about the project.

Thank you for contributing to VoceVibe!

