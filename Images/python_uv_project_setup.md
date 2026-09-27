# Python + `uv` Project Setup Notes

These notes summarize the setup used for the `Images` Python project,
with emphasis on **what each step does and why it is needed**.

------------------------------------------------------------------------

## 1. Start with a Project Folder

We created/opened a folder for the project:

``` text
Images/
```

Think of this as one independent Python project.

------------------------------------------------------------------------

## 2. Create a Virtual Environment

Run:

``` powershell
uv venv
```

This creates:

``` text
Images/
└── .venv/
```

### What is `uv`?

`uv` is a modern Python package and project management tool.

We use it to:

-   Create virtual environments
-   Install/add Python packages
-   Manage project dependencies
-   Lock dependency versions
-   Synchronize environments
-   Run Python code inside the project environment

### What is `.venv`?

`.venv` is the project's **virtual environment**.

It gives this project its own isolated Python environment and installed
packages.

Example:

``` text
Project A
└── .venv
    └── its packages

Project B
└── .venv
    └── its packages
```

This prevents dependencies required by one project from unnecessarily
interfering with another project.

**Remember:**

> `.venv` = WHERE this project's Python packages are installed.

------------------------------------------------------------------------

## 3. Activate the Virtual Environment

In PowerShell:

``` powershell
.venv\Scripts\Activate.ps1
```

After activation, the terminal normally shows something like:

``` text
(.venv) PS C:\...\Images>
```

This means the project's virtual environment is active.

You can then run commands such as:

``` powershell
python app.py
```

using that environment.

### Do we always need to activate it?

Not necessarily when using `uv`.

For example:

``` powershell
uv run python app.py
```

runs the program using the project's environment without requiring you
to manually activate `.venv` first.

------------------------------------------------------------------------

## 4. Install Packages

During initial setup we used commands such as:

``` powershell
uv pip install openai python-dotenv
```

and later:

``` powershell
uv pip install --upgrade "azure-ai-projects>=2.0.0" azure-identity openai python-dotenv
```

### What does `uv pip install` mean?

It means:

> Install these Python packages into the Python environment.

The packages used by this project include:

``` text
azure-ai-projects
azure-identity
openai
python-dotenv
```

### Why do we need them?

#### `azure-ai-projects`

Used to work with a Microsoft Foundry project.

Example:

``` python
from azure.ai.projects import AIProjectClient
```

#### `azure-identity`

Used for Azure authentication.

Example:

``` python
from azure.identity import DefaultAzureCredential
```

#### `openai`

Provides the OpenAI-compatible APIs used when communicating with
supported model deployments.

#### `python-dotenv`

Allows Python to load configuration values from a `.env` file.

Example:

``` python
from dotenv import load_dotenv
```

------------------------------------------------------------------------

## 5. What Does `--upgrade` Mean?

Example:

``` powershell
uv pip install --upgrade openai
```

`--upgrade` means:

> If an older compatible version is already installed, update it to an
> appropriate newer version.

For example:

``` text
"azure-ai-projects>=2.0.0"
```

means:

> Use version 2.0.0 or newer.

`>=` means **greater than or equal to**.

------------------------------------------------------------------------

## 6. `.env` vs `.venv`

These names look similar but are completely different.

### `.venv/`

The virtual Python environment.

``` text
.venv/
└── installed Python packages
```

### `.env`

A text file containing application configuration/environment variables.

Example:

``` text
PROJECT_ENDPOINT=...
MODEL_DEPLOYMENT_NAME=...
IMAGE_MODEL_DEPLOYMENT_NAME=...
```

Python loads it using:

``` python
load_dotenv()
```

and reads values using:

``` python
os.getenv("PROJECT_ENDPOINT")
```

### Easy memory rule

``` text
.venv = Python environment
.env  = Application configuration
```

------------------------------------------------------------------------

## 7. Why Dependency Tracking Is Needed

Installing packages into `.venv` makes the current computer work, but
another developer does not automatically know which packages the project
needs.

For example, if someone only receives:

``` text
app.py
```

and runs it without the dependencies, they may get:

``` text
ModuleNotFoundError
```

Therefore, a Python project should **record its dependencies**.

------------------------------------------------------------------------

## 8. Traditional `requirements.txt`

A traditional Python project may contain:

``` text
requirements.txt
```

Example:

``` text
azure-ai-projects
azure-identity
openai
python-dotenv
```

Then another developer can run:

``` powershell
pip install -r requirements.txt
```

or:

``` powershell
uv pip install -r requirements.txt
```

So:

> `requirements.txt` is a traditional way of listing project
> dependencies.

------------------------------------------------------------------------

## 9. Why We Use `pyproject.toml`

Because this project uses `uv`, we moved to the modern project workflow
using:

``` text
pyproject.toml
```

We initialized the project with:

``` powershell
uv init
```

This creates/configures the Python project metadata.

A simplified `pyproject.toml` may look like:

``` toml
[project]
name = "images"
version = "0.1.0"
requires-python = ">=3.13"

dependencies = [
    "azure-ai-projects",
    "azure-identity",
    "openai",
    "python-dotenv",
]
```

### .NET analogy

A useful analogy is:

``` text
.NET                     Python + uv
.csproj                  pyproject.toml
```

Both describe important project configuration and dependencies.

### Remember

> `pyproject.toml` = WHAT the Python project needs/configures.

------------------------------------------------------------------------

## 10. `uv add` vs `uv pip install`

This is an important distinction.

### `uv pip install`

``` powershell
uv pip install openai
```

Primarily means:

> Install `openai` into the environment.

### `uv add`

``` powershell
uv add openai
```

Means:

> Add `openai` as a dependency of this project and install/synchronize
> it.

For a proper `uv` project, prefer:

``` powershell
uv add azure-ai-projects azure-identity openai python-dotenv
```

This records the project dependencies in `pyproject.toml`.

------------------------------------------------------------------------

## 11. What Is `uv.lock`?

After dependency resolution, `uv` creates:

``` text
uv.lock
```

Suppose `pyproject.toml` says:

``` text
openai >= 2.0
```

There may be many versions satisfying that requirement.

`uv` resolves the dependency tree to specific package versions.

Conceptually:

``` text
pyproject.toml
openai >= 2.0
      ↓
uv resolves dependencies
      ↓
uv.lock
openai = exact resolved version
httpx = exact resolved version
other dependencies = exact resolved versions
```

So:

> `pyproject.toml` = what packages/project requirements we declare.

> `uv.lock` = the exact dependency versions `uv` resolved for a
> reproducible environment.

The lock file also includes **transitive dependencies** --- packages
required by the packages you directly added.

------------------------------------------------------------------------

## 12. What If `uv.lock` Is Deleted?

The project is not automatically destroyed.

`uv` can resolve dependencies again from `pyproject.toml` and generate a
new lock file.

However:

``` text
Old uv.lock
    ↓
exact dependency set A
```

If you delete it and resolve again later:

``` text
pyproject.toml
    ↓
new dependency resolution
    ↓
New uv.lock
    ↓
possibly dependency set B
```

Newer compatible package versions may now exist.

Therefore:

> Keep `uv.lock` when you want reproducible dependency resolution.

It is normally committed to source control for an application project.

------------------------------------------------------------------------

## 13. What Does `uv sync` Do?

Run:

``` powershell
uv sync
```

Conceptually:

``` text
pyproject.toml
      +
   uv.lock
      ↓
   uv sync
      ↓
    .venv
```

It synchronizes the project's environment with the dependencies
defined/resolved for the project.

This is useful after cloning/copying a project.

------------------------------------------------------------------------

## 14. Do We Share `.venv`?

Normally, **no**.

You usually share/commit project files such as:

``` text
app.py
pyproject.toml
uv.lock
```

but not the entire:

``` text
.venv/
```

Another developer can recreate the environment with:

``` powershell
uv sync
```

------------------------------------------------------------------------

## 15. Running the Application with `uv`

Instead of manually activating `.venv`, you can run:

``` powershell
uv run python app.py
```

Conceptually:

``` text
uv
 ↓
uses project environment
 ↓
Python
 ↓
app.py
```

This is convenient because `uv` handles the project environment for the
command.

------------------------------------------------------------------------

# Current Project Structure

Our learning project is approximately:

``` text
Images/
│
├── .venv/
├── .env
├── app.py
├── factory.jpg
├── pyproject.toml
└── uv.lock
```

As we add the image-generation practical, we will also have:

``` text
generate_image.py
```

------------------------------------------------------------------------

# What Each File Does

  File / Folder         Purpose
  --------------------- ----------------------------------------------------
  `Images/`             Project folder
  `.venv/`              Isolated Python environment and installed packages
  `.env`                Application configuration/environment variables
  `pyproject.toml`      Python project metadata and declared dependencies
  `uv.lock`             Exact dependency versions resolved by `uv`
  `app.py`              Multimodal image-understanding practical
  `factory.jpg`         Local image used as input
  `generate_image.py`   Image-generation practical

------------------------------------------------------------------------

# Commands to Remember

## Create a virtual environment

``` powershell
uv venv
```

## Activate it manually in PowerShell

``` powershell
.venv\Scripts\Activate.ps1
```

## Initialize a uv project

``` powershell
uv init
```

## Add a project dependency

``` powershell
uv add <package>
```

Example:

``` powershell
uv add openai
```

## Synchronize the project environment

``` powershell
uv sync
```

## Run a Python program using the project environment

``` powershell
uv run python app.py
```

------------------------------------------------------------------------

# Final Mental Model

``` text
                    PYTHON PROJECT
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
 pyproject.toml       uv.lock            .env
        │                │                 │
 WHAT dependencies   EXACT resolved     Application
 project declares    dependency set     configuration
        │                │                 │
        └────────┬───────┘                 │
                 ↓                         │
              uv sync                     │
                 ↓                         │
               .venv                      │
                 │                         │
          installed packages              │
                 │                         │
                 └──────────┬──────────────┘
                            ↓
                          app.py
                            ↓
                    Python application
```

## One-Line Memory

``` text
uv              = Python project/package manager
.venv           = isolated Python environment
.env            = application configuration
pyproject.toml  = declared project configuration/dependencies
uv.lock         = exact resolved dependency versions
uv sync         = make environment match the project
uv run          = run a command in the project environment
```
