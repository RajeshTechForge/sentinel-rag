# 🎉 Welcome to **Sentinel RAG**! 

We're excited that you're interested in contributing to our project!  
We want to ensure that every user and contributor feels welcome, included and supported to participate in sentinel-rag community. This guide will help you get started and ensure your contributions can be efficiently integrated into the project.

## Documentation

- [Configuration Guide](docs/CONFIGURATION.md) - To create custom `config.json` for your organization
- [Compliance Guide](docs/COMPLIANCE_GUIDE.md) - Audit logging for GDPR, HIPAA, SOC2 considerations


## 1. 🚀 Ways to Contribute

You can contribute to **Sentinel RAG** in many ways:

- 📝 Submitting bug reports or feature requests
- 💡 Improving documentation
- 🔍 Reviewing pull requests
- 🛠️ Contributing code or tests
- 🌐 Helping other users

## Issue Labels

To help you find the most appropriate issues to work on, we use the following labels:

- `good first issue` - Perfect for newcomers to the project
- `bug` - Something isn't working as expected
- `documentation` - Improvements or additions to documentation
- `enhancement` - New features or improvements
- `help wanted` - Extra attention or assistance needed
- `question` - Further information is requested
- `wontfix` - This will not be worked on

Looking for a place to start? Try filtering for [good first issues](https://github.com/RajeshTechForge/sentinel-rag/labels/good%20first%20issue)!


## 2. 🛠️ Development Setup

### Fork and Clone

1. Fork the [**sentinel-rag**](https://github.com/RajeshTechForge/sentinel-rag) repository
2. Clone your fork:
   ```shell
   git clone https://github.com/<your-github-username>/sentinel-rag.git
   cd sentinel-rag
   ```

### Create a Branch

Create a new branch for your work:
```shell
git checkout -b feature/your-feature-name
```

## 3. 🎯 Developing

### Usage of uv

We use [uv](https://docs.astral.sh/uv/) as package and project manager.

#### Installation

To install `uv`, check the documentation on [Installing uv](https://docs.astral.sh/uv/getting-started/installation/).

#### Create an environment and sync it

You can use the `uv sync` to create a project virtual environment (if it does not already exist) and sync
the project's dependencies with the environment.

```bash
uv sync
```

#### Use a specific Python version (optional)

If you need to work with a specific version of Python, you can create a new virtual environment for that version
and run the sync command:

```bash
uv venv --python 3.11
uv sync
```

More detailed options are described on the [Using Python environments](https://docs.astral.sh/uv/pip/environments/) documentation.

#### Add a new dependency

Simply use the `uv add` command. The `pyproject.toml` and `uv.lock` files will be updated.

### Making Changes

1. **Code Style**: Follow the project's coding standards
2. **Documentation**: Update relevant documentation
3. **Commits**: Write clear commit messages


## 4. 📤 Submitting Changes

1. Install ruff on your system
2. Run ```ruff format .``` and ``` ruff check ``` and fix the issues
3. Push your changes:
   ```shell
   git add .
   git commit -m "Description of your changes"
   git push origin feature/your-feature-name
   ```
2. Create a Pull Request:
   - Go to the [**sentinel-rag** repository](https://github.com/RajeshTechForge/sentinel-rag)
   - Click "Compare & Pull Request" and open a PR against dev branch
   - Fill in the PR template with details about your changes


## 5. 🤝 Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Follow our [Code of Conduct](CODE_OF_CONDUCT.md)
- Provide constructive feedback
- Ask questions when unsure
