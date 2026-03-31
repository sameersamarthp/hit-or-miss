"""
expand_dataset.py

Expands test_prompts.json from 64 groups to 100 groups:
  - For each of the 64 existing groups: adds 2 more paraphrases (medium + hard)
    and 1 more close_but_different variant
  - Adds 36 new groups:
      - 10 devops groups
      - 10 ml_data_science groups
      - 16 groups across the existing 8 domains (2 per domain)
"""

import json
import os

# ---------------------------------------------------------------------------
# ADDITIONAL VARIANTS FOR THE 64 EXISTING GROUPS
# ---------------------------------------------------------------------------
# Key = group id, value = dict with:
#   "paraphrase": [medium_paraphrase, hard_paraphrase]
#   "close_but_different": [extra_variant]

EXTRA_VARIANTS: dict[str, dict] = {
    # ---- data_structures ----
    "linked_list_reverse": {
        "paraphrase": [
            "Write me a Python solution that reverses the nodes of a singly linked list in-place",
            "Given a singly linked list, produce Python code that returns it in reversed order by relinking nodes",
        ],
        "close_but_different": [
            "Write a Python function to remove duplicate nodes from a singly linked list"
        ],
    },
    "binary_tree_inorder": {
        "paraphrase": [
            "Code up inorder (LNR) traversal for a binary tree in Python",
            "Provide a Python implementation of in-order binary tree traversal that works iteratively with a stack",
        ],
        "close_but_different": [
            "Write a Python function to perform postorder traversal of a binary tree"
        ],
    },
    "stack_balanced_parens": {
        "paraphrase": [
            "Show me Python code using a stack to decide if a string's brackets are balanced",
            "Implement bracket-balance checking in Python — the solution must work for (), [], and {}",
        ],
        "close_but_different": [
            "Write a Python function that returns the minimum number of bracket insertions to balance a string"
        ],
    },
    "binary_search": {
        "paraphrase": [
            "Give me an iterative Python implementation of binary search on a sorted array",
            "Implement binary search in Python without recursion, returning -1 if the target is absent",
        ],
        "close_but_different": [
            "Write a Python function to find the insertion position for a target value in a sorted list using binary search"
        ],
    },
    "merge_sort": {
        "paraphrase": [
            "Implement merge sort in Python that splits a list in half, sorts each half, then merges",
            "Show me a Python function that uses the merge sort technique to sort a list of integers",
        ],
        "close_but_different": [
            "Write a Python function to sort a list using heapsort"
        ],
    },
    "graph_bfs": {
        "paraphrase": [
            "Write Python code for BFS on a graph using a queue and visited set",
            "Implement breadth-first graph traversal in Python that returns nodes in BFS order",
        ],
        "close_but_different": [
            "Write a Python function to count the number of connected components in an undirected graph using BFS"
        ],
    },
    "lru_cache": {
        "paraphrase": [
            "Build an LRU cache in Python backed by an OrderedDict with O(1) get/put",
            "Implement a capacity-bounded LRU cache in Python — accessing an item should move it to the front",
        ],
        "close_but_different": [
            "Implement a fixed-capacity FIFO cache in Python with get and put operations"
        ],
    },
    "trie_insert_search": {
        "paraphrase": [
            "Implement a prefix tree in Python supporting word insertion and membership testing",
            "Build a Trie class in Python where insert adds a word and search checks if the exact word was inserted",
        ],
        "close_but_different": [
            "Implement a Trie in Python that supports deleting a word without removing shared prefixes"
        ],
    },
    # ---- api_development ----
    "fastapi_crud_route": {
        "paraphrase": [
            "Build GET, POST, PUT, DELETE FastAPI endpoints for a User entity stored in a dict",
            "Show me how to wire up a full CRUD REST API for users in FastAPI with path and body parameters",
        ],
        "close_but_different": [
            "Write FastAPI routes that handle CRUD for an Order model with status transitions"
        ],
    },
    "fastapi_jwt_auth": {
        "paraphrase": [
            "Show me FastAPI code that validates a JWT Bearer token in an HTTP Authorization header",
            "Create a FastAPI security dependency that decodes and verifies a JWT, raising 401 on failure",
        ],
        "close_but_different": [
            "Write a FastAPI dependency that checks for a valid OAuth2 access token using an introspection endpoint"
        ],
    },
    "flask_blueprint": {
        "paraphrase": [
            "Demonstrate organizing a Flask app into multiple Blueprint modules with their own route prefixes",
            "Show me a Flask project layout where auth routes and admin routes each live in separate Blueprint files",
        ],
        "close_but_different": [
            "How do I register a Flask Blueprint with a custom url_prefix and subdomain?"
        ],
    },
    "fastapi_request_validation": {
        "paraphrase": [
            "Show me how Pydantic BaseModel is used in a FastAPI POST endpoint to auto-validate JSON fields",
            "Demonstrate defining a Pydantic request schema in FastAPI so that missing required fields return 422",
        ],
        "close_but_different": [
            "How do I use Pydantic validators in FastAPI to enforce a custom field constraint like minimum length?"
        ],
    },
    "fastapi_background_tasks": {
        "paraphrase": [
            "Demonstrate using FastAPI BackgroundTasks to send an email after the HTTP response is returned",
            "Show me the FastAPI pattern for kicking off a non-blocking job while immediately responding to the client",
        ],
        "close_but_different": [
            "How do I schedule a repeating background task in FastAPI using asyncio.create_task?"
        ],
    },
    "fastapi_rate_limiting": {
        "paraphrase": [
            "Show me FastAPI middleware that tracks request counts per IP and returns 429 when a limit is exceeded",
            "Implement token-bucket rate limiting per IP address in a FastAPI application",
        ],
        "close_but_different": [
            "How do I implement rate limiting in FastAPI based on an authenticated user's plan tier?"
        ],
    },
    "fastapi_websocket": {
        "paraphrase": [
            "Show me a FastAPI WebSocket endpoint that echoes messages back to the connected client",
            "Implement a chat room WebSocket in FastAPI where each connected client receives all broadcast messages",
        ],
        "close_but_different": [
            "How do I authenticate a WebSocket connection in FastAPI using a token passed as a query parameter?"
        ],
    },
    "flask_error_handler": {
        "paraphrase": [
            "Show me how to use @app.errorhandler in Flask to return JSON for 404 and 500 errors",
            "Implement Flask error handlers that catch HTTP exceptions and always respond with a JSON error body",
        ],
        "close_but_different": [
            "How do I create a Flask error handler that catches all unhandled exceptions and logs a traceback?"
        ],
    },
    # ---- file_io ----
    "read_csv_to_dicts": {
        "paraphrase": [
            "Show me Python code that opens a CSV with csv.DictReader and returns all rows as a list of dicts",
            "Write a Python function using the csv module that parses a file and returns a list where each item is a row dict",
        ],
        "close_but_different": [
            "Write a Python function to read a TSV (tab-separated) file and return a list of dictionaries"
        ],
    },
    "write_json_file": {
        "paraphrase": [
            "Implement a Python function that opens a file for writing and uses json.dump with indent=2",
            "Show me how to persist a Python dict to a .json file with pretty-printing using the json module",
        ],
        "close_but_different": [
            "Write a Python function to append a dictionary as a new JSON line to an existing JSONL file"
        ],
    },
    "recursive_directory_walk": {
        "paraphrase": [
            "Show me how to use pathlib.Path.rglob to collect all files under a directory in Python",
            "Implement a Python generator that walks a directory tree and yields the absolute path of every file",
        ],
        "close_but_different": [
            "Write a Python function to recursively find all files larger than a given size in bytes under a directory"
        ],
    },
    "read_write_text_file": {
        "paraphrase": [
            "Give me Python code that reads a file and yields only the lines that contain non-whitespace characters",
            "Write a Python function that opens a text file and returns a list of stripped non-empty lines",
        ],
        "close_but_different": [
            "Write a Python function to read a text file and return only lines that start with a specific prefix"
        ],
    },
    "watch_file_changes": {
        "paraphrase": [
            "Show me how to poll a file's mtime in a loop in Python and invoke a callback when it changes",
            "Write a Python file watcher using watchdog that triggers a function when a specific file is modified",
        ],
        "close_but_different": [
            "How do I use inotify in Python to watch a directory for newly created files?"
        ],
    },
    "atomic_file_write": {
        "paraphrase": [
            "Show me a Python function that writes data to a tempfile and atomically replaces the target using os.replace",
            "Demonstrate safe atomic file writes in Python: write to a temp path, then rename to avoid partial writes",
        ],
        "close_but_different": [
            "How do I use fcntl.flock in Python to acquire an exclusive file lock before writing?"
        ],
    },
    "parse_config_ini": {
        "paraphrase": [
            "Show me Python code using configparser to load an INI file and access a value from a specific section",
            "Demonstrate reading a .cfg file in Python with ConfigParser and falling back to a default if a key is missing",
        ],
        "close_but_different": [
            "How do I use Python's configparser to write updated settings back to an INI file?"
        ],
    },
    "compress_files_zip": {
        "paraphrase": [
            "Show me Python code using zipfile.ZipFile to add multiple files to a new zip archive",
            "Implement a Python function that takes a directory path and zips all its contents into a .zip file",
        ],
        "close_but_different": [
            "Write a Python function to list all files inside an existing zip archive without extracting them"
        ],
    },
    # ---- database ----
    "sqlalchemy_model_definition": {
        "paraphrase": [
            "Show me a SQLAlchemy ORM class using DeclarativeBase that maps to a users table with id, name, email fields",
            "Demonstrate defining a SQLAlchemy 2.0-style mapped_column model for a User with an auto-increment primary key",
        ],
        "close_but_different": [
            "How do I define a SQLAlchemy ORM model with a composite primary key across two columns?"
        ],
    },
    "sqlalchemy_session_query": {
        "paraphrase": [
            "Show me how to use session.execute(select(User).where(...)) in SQLAlchemy 2.0 to filter rows",
            "Demonstrate using the SQLAlchemy ORM to fetch all rows matching a filter condition with scalars()",
        ],
        "close_but_different": [
            "How do I perform a case-insensitive filter on a string column in SQLAlchemy ORM?"
        ],
    },
    "alembic_migration": {
        "paraphrase": [
            "Explain the alembic revision --autogenerate and alembic upgrade head workflow for adding a column",
            "Show me an Alembic upgrade() function that adds a nullable varchar column to an existing table",
        ],
        "close_but_different": [
            "How do I write an Alembic migration to add an index to an existing column?"
        ],
    },
    "raw_sql_query": {
        "paraphrase": [
            "Show me how to use SQLAlchemy text() with bindparams to run a safe parameterized raw SQL query",
            "Demonstrate executing a raw SQL SELECT with named parameters in SQLAlchemy to prevent injection",
        ],
        "close_but_different": [
            "How do I use SQLAlchemy Core to execute a raw SQL UPDATE with bound parameters?"
        ],
    },
    "postgresql_connection_pool": {
        "paraphrase": [
            "Show me how to call asyncpg.create_pool() and acquire connections for PostgreSQL queries",
            "Demonstrate initializing an asyncpg connection pool in a FastAPI lifespan and using it in a route",
        ],
        "close_but_different": [
            "How do I configure SQLAlchemy's async engine with asyncpg as the driver for PostgreSQL?"
        ],
    },
    "sqlite_in_memory_tests": {
        "paraphrase": [
            "Show me how to create an in-memory SQLite engine in SQLAlchemy and run tests against it",
            "Demonstrate setting up pytest fixtures that create and drop all SQLAlchemy tables using an in-memory SQLite DB",
        ],
        "close_but_different": [
            "How do I use pytest with a real PostgreSQL database via a test-specific schema instead of in-memory SQLite?"
        ],
    },
    "upsert_on_conflict": {
        "paraphrase": [
            "Show me how to use PostgreSQL's INSERT ... ON CONFLICT DO UPDATE via SQLAlchemy's insert().on_conflict_do_update()",
            "Demonstrate an upsert in SQLAlchemy that inserts a new row or updates an existing one on a unique constraint conflict",
        ],
        "close_but_different": [
            "How do I use SQLAlchemy's merge() method to implement an upsert-like operation?"
        ],
    },
    "db_pagination": {
        "paraphrase": [
            "Show me SQLAlchemy code to apply .limit(page_size).offset(page * page_size) to paginate query results",
            "Implement a Python function that returns a specific page of SQLAlchemy ORM results along with the total count",
        ],
        "close_but_different": [
            "How do I implement keyset (seek-method) pagination in SQLAlchemy to avoid offset performance issues?"
        ],
    },
    # ---- async_programming ----
    "asyncio_gather": {
        "paraphrase": [
            "Give me a Python example using asyncio.gather(*tasks) to run several coroutines and collect all results",
            "Show me how asyncio.gather works to fan-out multiple async calls and await them all in Python",
        ],
        "close_but_different": [
            "How do I use asyncio.gather with return_exceptions=True to handle errors from individual tasks?"
        ],
    },
    "asyncio_producer_consumer": {
        "paraphrase": [
            "Show me async Python code where a producer coroutine puts items into an asyncio.Queue and a consumer drains it",
            "Implement an asyncio pipeline with multiple worker coroutines consuming from a shared Queue",
        ],
        "close_but_different": [
            "How do I implement backpressure in an asyncio producer-consumer system using a bounded queue?"
        ],
    },
    "asyncio_timeout": {
        "paraphrase": [
            "Show me how to wrap an asyncio coroutine with asyncio.wait_for and handle asyncio.TimeoutError",
            "Demonstrate Python asyncio code that cancels a slow coroutine after a deadline using asyncio.timeout()",
        ],
        "close_but_different": [
            "How do I implement a circuit breaker pattern in Python asyncio that stops calling a slow service?"
        ],
    },
    "async_http_client": {
        "paraphrase": [
            "Show me how to use async with httpx.AsyncClient() to make concurrent GET requests with asyncio.gather",
            "Give me Python code that fires 10 async HTTP requests simultaneously using httpx and collects the responses",
        ],
        "close_but_different": [
            "How do I stream a large HTTP response body in Python using httpx AsyncClient without loading it into memory?"
        ],
    },
    "asyncio_semaphore": {
        "paraphrase": [
            "Give me a Python example that wraps each asyncio task in an async with semaphore block to limit concurrency",
            "Show me how asyncio.Semaphore(N) prevents more than N tasks from running at once in a Python async program",
        ],
        "close_but_different": [
            "How do I use asyncio.Semaphore to rate-limit API calls to a maximum of 5 per second in Python?"
        ],
    },
    "async_context_manager": {
        "paraphrase": [
            "Show me a complete Python class with async __aenter__ and __aexit__ methods usable with async with",
            "Implement an async context manager in Python that opens a resource on enter and closes it on exit",
        ],
        "close_but_different": [
            "How do I combine @contextlib.asynccontextmanager with a try/finally to clean up an async resource?"
        ],
    },
    "event_loop_run": {
        "paraphrase": [
            "Show me how to call asyncio.run(my_coroutine()) to execute an async function from a synchronous script",
            "Demonstrate running a single asyncio coroutine synchronously using asyncio.run in a Python __main__ block",
        ],
        "close_but_different": [
            "How do I get an existing asyncio event loop and submit a coroutine to it from a thread in Python?"
        ],
    },
    "async_generator": {
        "paraphrase": [
            "Show me a Python async generator that fetches pages from an API and yields items one by one",
            "Implement an async def generator in Python that uses await inside its loop and yields results incrementally",
        ],
        "close_but_different": [
            "How do I convert a synchronous generator to an async generator in Python so it can be used with async for?"
        ],
    },
    # ---- testing ----
    "pytest_fixture_scope": {
        "paraphrase": [
            "Show me how scope='session' on a pytest fixture makes it initialize once for all tests in the run",
            "Demonstrate a session-scoped pytest fixture that creates a database connection once and shares it across tests",
        ],
        "close_but_different": [
            "How do I write a pytest fixture with class scope that is shared across all tests in a test class?"
        ],
    },
    "pytest_parametrize": {
        "paraphrase": [
            "Show me @pytest.mark.parametrize with a list of (input, expected) tuples for a single test function",
            "Demonstrate using pytest parametrize to test a function with edge cases: empty input, single item, and large list",
        ],
        "close_but_different": [
            "How do I use pytest parametrize with ids= to give each parametrized case a descriptive name?"
        ],
    },
    "pytest_mock_patch": {
        "paraphrase": [
            "Demonstrate using @patch('module.function_name') as a decorator on a pytest test to replace a function",
            "Show me how to use patch as a context manager inside a pytest test to swap out an external dependency",
        ],
        "close_but_different": [
            "How do I use unittest.mock.patch.object to mock a method on an instance during a pytest test?"
        ],
    },
    "pytest_custom_assertion": {
        "paraphrase": [
            "Show me a pytest helper function that asserts two dicts are equal and prints a diff on failure",
            "Implement a reusable pytest assertion utility that checks a response object has a specific HTTP status and body",
        ],
        "close_but_different": [
            "How do I write a pytest plugin that adds a custom assert introspection rewriter for a domain object?"
        ],
    },
    "pytest_tmp_directory": {
        "paraphrase": [
            "Show me how to use the pytest tmp_path fixture to write a file and then read it back in a test",
            "Demonstrate a pytest test that creates a temporary JSON config file using tmp_path and reads it with the code under test",
        ],
        "close_but_different": [
            "How do I use pytest's tmp_path_factory to create a shared temporary directory across multiple tests?"
        ],
    },
    "pytest_exception_raises": {
        "paraphrase": [
            "Show me pytest.raises used as a context manager to verify a function raises ValueError with a specific message",
            "Demonstrate testing that a class constructor raises TypeError for invalid arguments using pytest.raises",
        ],
        "close_but_different": [
            "How do I use pytest.warns to assert that a function emits a DeprecationWarning?"
        ],
    },
    "pytest_async_test": {
        "paraphrase": [
            "Show me a @pytest.mark.asyncio test that awaits an async function and checks its return value",
            "Demonstrate writing a pytest-asyncio test for an async database access function that returns a list",
        ],
        "close_but_different": [
            "How do I write a pytest-asyncio test that mocks an async HTTP call using AsyncMock?"
        ],
    },
    "pytest_conftest": {
        "paraphrase": [
            "Show me a conftest.py that defines a client fixture using FastAPI TestClient shared across multiple test files",
            "Demonstrate placing a database fixture in conftest.py so all test modules can use it without importing",
        ],
        "close_but_different": [
            "How do I place a conftest.py at different directory levels to scope fixtures to subpackages in pytest?"
        ],
    },
    # ---- cli_tools ----
    "argparse_subcommands": {
        "paraphrase": [
            "Show me argparse subparsers where each subcommand has its own set of required and optional arguments",
            "Demonstrate building a Python CLI with argparse that has 'init', 'run', and 'status' subcommands",
        ],
        "close_but_different": [
            "How do I add aliases to argparse subcommands so 'st' works as a shorthand for 'status'?"
        ],
    },
    "click_command_group": {
        "paraphrase": [
            "Show me Click's @group and @command decorators to build a CLI where commands share a common option",
            "Demonstrate a Click CLI group where each subcommand is defined in a separate function using @cli.command()",
        ],
        "close_but_different": [
            "How do I use Click's result_callback on a group to run code after any subcommand completes?"
        ],
    },
    "cli_stdin_pipe": {
        "paraphrase": [
            "Show me Python code that checks if sys.stdin is a tty to decide between reading a file argument or piped input",
            "Implement a CLI utility in Python using Click that accepts an optional filename, falling back to stdin",
        ],
        "close_but_different": [
            "How do I write a Python CLI script that processes multiple input files passed as positional arguments?"
        ],
    },
    "click_progress_bar": {
        "paraphrase": [
            "Show me Click's click.progressbar() context manager wrapping an iterable to display a live progress bar",
            "Implement a Click CLI command that processes items from a list and shows completion percentage with click.progressbar",
        ],
        "close_but_different": [
            "How do I display an indeterminate spinner in a Python CLI while a long-running async task completes?"
        ],
    },
    "cli_config_file": {
        "paraphrase": [
            "Show me Click's auto_envvar_prefix combined with a config file to layer CLI > env > config file defaults",
            "Demonstrate a Click command that reads default values from a TOML config file when options are not passed",
        ],
        "close_but_different": [
            "How do I use Click's Context.default_map to set default option values programmatically?"
        ],
    },
    "cli_colorized_output": {
        "paraphrase": [
            "Show me how to use click.style() and click.echo() to print green and red colored text in a CLI",
            "Implement a Python CLI helper that prints success in green, warnings in yellow, and errors in red using colorama",
        ],
        "close_but_different": [
            "How do I detect if the terminal supports color in Python and disable ANSI codes when piped to a file?"
        ],
    },
    "cli_interactive_prompt": {
        "paraphrase": [
            "Show me click.confirm() used to ask 'Are you sure?' before executing a destructive CLI command",
            "Demonstrate a Python CLI that prompts for confirmation with a default of 'no' before deleting records",
        ],
        "close_but_different": [
            "How do I use Click to display a multi-choice menu and let the user pick an option interactively?"
        ],
    },
    "argparse_type_validation": {
        "paraphrase": [
            "Show me an argparse type= function that raises ArgumentTypeError when a port number is out of range",
            "Demonstrate writing a custom argparse type validator that parses a date string and rejects invalid formats",
        ],
        "close_but_different": [
            "How do I restrict an argparse argument to a fixed set of string choices and show them in the help?"
        ],
    },
    # ---- string_manipulation ----
    "regex_email_extraction": {
        "paraphrase": [
            "Show me how to use re.findall with a pattern that matches standard email addresses in Python",
            "Write a Python function that uses a compiled regex pattern to extract all emails from a multiline string",
        ],
        "close_but_different": [
            "Write a Python function to extract all URLs from a block of text using regex"
        ],
    },
    "string_camel_to_snake": {
        "paraphrase": [
            "Show me Python regex that inserts underscores before uppercase letters to convert camelCase to snake_case",
            "Implement camelCase-to-snake_case conversion in Python handling consecutive uppercase letters like 'HTMLParser'",
        ],
        "close_but_different": [
            "Write a Python function to convert a kebab-case string to snake_case"
        ],
    },
    "string_truncate_ellipsis": {
        "paraphrase": [
            "Show me a Python one-liner that returns the first N chars of a string followed by '...' if it was longer",
            "Write a Python function that clips text to max_length characters and appends an ellipsis only if clipped",
        ],
        "close_but_different": [
            "Write a Python function to center-truncate a string so it fits in a fixed width with '...' in the middle"
        ],
    },
    "regex_url_validation": {
        "paraphrase": [
            "Show me a Python regex pattern that matches http:// and https:// URLs including query strings",
            "Implement a Python function using re.fullmatch to check if a string is a valid URL with optional path and params",
        ],
        "close_but_different": [
            "Write a Python function to extract the scheme, host, and path components from a URL string"
        ],
    },
    "string_count_words": {
        "paraphrase": [
            "Show me Python code using collections.Counter to compute word frequencies from a lowercased string",
            "Implement a Python function that tokenizes a string on whitespace, lowercases each token, and returns a frequency dict",
        ],
        "close_but_different": [
            "Write a Python function to count the frequency of bigrams (two-word pairs) in a string"
        ],
    },
    "string_format_template": {
        "paraphrase": [
            "Show me how string.Template.safe_substitute() differs from substitute() and when to use it in Python",
            "Demonstrate using string.Template to render a message template from a dict while ignoring missing keys",
        ],
        "close_but_different": [
            "How do I use Python's str.format_map() with a defaultdict to substitute variables and keep missing ones intact?"
        ],
    },
    "base64_encode_decode": {
        "paraphrase": [
            "Show me Python code that calls base64.b64encode(text.encode()).decode() to get a base64 string",
            "Implement Python functions that round-trip a string through base64 encoding and decoding",
        ],
        "close_but_different": [
            "Write a Python function to encode a file's binary contents to a base64 string for embedding in JSON"
        ],
    },
    "string_levenshtein": {
        "paraphrase": [
            "Show me a dynamic programming solution in Python for computing edit distance between two strings",
            "Implement Levenshtein distance in Python using a 2D DP matrix and explain each cell's meaning",
        ],
        "close_but_different": [
            "Write a Python function to compute the Damerau-Levenshtein distance that also counts transpositions"
        ],
    },
}


# ---------------------------------------------------------------------------
# 36 NEW GROUPS
# ---------------------------------------------------------------------------

NEW_GROUPS = [
    # ================================================================
    # devops (10 groups)
    # ================================================================
    {
        "id": "dockerfile_python_app",
        "domain": "devops",
        "base_prompt": "Write a Dockerfile for a Python FastAPI application that runs with uvicorn",
        "variants": {
            "exact_duplicate": [
                "Write a Dockerfile for a Python FastAPI application that runs with uvicorn"
            ],
            "paraphrase": [
                "How do I containerize a FastAPI app using Docker?",
                "Give me a Dockerfile that sets up a Python web service with uvicorn",
                "Create a Docker image definition for a FastAPI application using uvicorn as the server",
                "Show me a Dockerfile for deploying a Python ASGI app with uvicorn in a container",
                "What should my Dockerfile look like to run a FastAPI project inside Docker using uvicorn?",
            ],
            "close_but_different": [
                "Write a Dockerfile for a Python FastAPI application that runs with gunicorn and uvicorn workers",
                "Write a Dockerfile for a Node.js Express application that runs with node",
                "Write a multi-stage Dockerfile for a Python FastAPI app that minimizes the final image size",
            ],
            "unrelated": [
                "How do I implement a trie in Python to autocomplete search queries?"
            ],
        },
    },
    {
        "id": "docker_compose_postgres",
        "domain": "devops",
        "base_prompt": "Write a docker-compose.yml that runs a Python web app alongside a PostgreSQL database",
        "variants": {
            "exact_duplicate": [
                "Write a docker-compose.yml that runs a Python web app alongside a PostgreSQL database"
            ],
            "paraphrase": [
                "How do I use Docker Compose to run my Python app with a Postgres service?",
                "Give me a compose file that brings up a web service and a PostgreSQL container together",
                "Create a docker-compose configuration for a Python API service and a Postgres database",
                "Show me a docker-compose.yml that links a FastAPI container to a PostgreSQL container",
                "What does a Docker Compose file look like when I want a Python app and Postgres to share a network?",
            ],
            "close_but_different": [
                "Write a docker-compose.yml that runs a Python web app alongside a MySQL database",
                "Write a docker-compose.yml that runs a Python web app alongside a Redis cache",
                "Write a docker-compose.yml that adds a pgAdmin service to manage the PostgreSQL database",
            ],
            "unrelated": [
                "How do I write a pytest fixture that provides a pre-populated SQLAlchemy session?"
            ],
        },
    },
    {
        "id": "github_actions_ci",
        "domain": "devops",
        "base_prompt": "Write a GitHub Actions workflow to run pytest tests on every pull request",
        "variants": {
            "exact_duplicate": [
                "Write a GitHub Actions workflow to run pytest tests on every pull request"
            ],
            "paraphrase": [
                "How do I set up CI with GitHub Actions to automatically run my Python test suite on PRs?",
                "Give me a .github/workflows YAML that installs Python dependencies and runs pytest on pull requests",
                "Create a GitHub Actions CI pipeline that executes pytest whenever a PR is opened or updated",
                "Show me a GitHub Actions workflow file that checks out code, installs requirements, and runs pytest",
                "What should my GitHub Actions YAML look like to trigger pytest on every new pull request?",
            ],
            "close_but_different": [
                "Write a GitHub Actions workflow to run pytest tests on every push to the main branch",
                "Write a GitHub Actions workflow to build and push a Docker image on every release tag",
                "Write a GitHub Actions workflow to run pytest with coverage and upload results to Codecov",
            ],
            "unrelated": [
                "How do I use Python's heapq.nlargest to find the top-K elements from a list?"
            ],
        },
    },
    {
        "id": "terraform_aws_ec2",
        "domain": "devops",
        "base_prompt": "Write a Terraform configuration to provision an AWS EC2 instance with a security group",
        "variants": {
            "exact_duplicate": [
                "Write a Terraform configuration to provision an AWS EC2 instance with a security group"
            ],
            "paraphrase": [
                "How do I use Terraform to create an EC2 instance on AWS with proper security group rules?",
                "Give me Terraform HCL that spins up an AWS EC2 instance and opens port 80 inbound",
                "Create a Terraform resource block for an EC2 instance and a security group allowing HTTP traffic",
                "Show me Terraform code that provisions a t2.micro EC2 instance with an attached security group",
                "What Terraform configuration do I need to launch an EC2 instance with a security group on AWS?",
            ],
            "close_but_different": [
                "Write a Terraform configuration to provision an AWS RDS PostgreSQL instance with a security group",
                "Write a Terraform configuration to provision an AWS Lambda function with an IAM role",
                "Write a Terraform configuration to provision an EC2 instance with an Elastic IP and security group",
            ],
            "unrelated": [
                "How do I use Python asyncio to stream lines from a subprocess in real time?"
            ],
        },
    },
    {
        "id": "nginx_reverse_proxy",
        "domain": "devops",
        "base_prompt": "Write an Nginx configuration to reverse proxy requests to a Python backend running on port 8000",
        "variants": {
            "exact_duplicate": [
                "Write an Nginx configuration to reverse proxy requests to a Python backend running on port 8000"
            ],
            "paraphrase": [
                "How do I configure Nginx to forward incoming HTTP requests to my Python app on port 8000?",
                "Give me an nginx.conf that proxies all traffic to a local server listening on port 8000",
                "Create an Nginx server block that acts as a reverse proxy to a backend on localhost:8000",
                "Show me the Nginx config for proxying web traffic to a FastAPI service on port 8000",
                "What should my nginx.conf look like to sit in front of a Python ASGI app running on 8000?",
            ],
            "close_but_different": [
                "Write an Nginx configuration to reverse proxy requests to a Node.js backend running on port 3000",
                "Write an Nginx configuration that load balances across three backend servers on different ports",
                "Write an Nginx configuration to serve static files and reverse proxy API requests to port 8000",
            ],
            "unrelated": [
                "How do I use Python's bisect module to maintain a sorted list efficiently?"
            ],
        },
    },
    {
        "id": "env_var_management",
        "domain": "devops",
        "base_prompt": "How do I manage environment variables for a Python application across development, staging, and production?",
        "variants": {
            "exact_duplicate": [
                "How do I manage environment variables for a Python application across development, staging, and production?"
            ],
            "paraphrase": [
                "What is the best way to handle different configs for dev, staging, and prod in a Python project?",
                "How can I use .env files and python-dotenv to manage environment-specific settings in Python?",
                "Show me a pattern for separating development and production environment variables in a Python app",
                "Give me a Python project setup that loads the right environment variables based on the current environment",
                "How should I structure .env files for multiple deployment environments in a Python application?",
            ],
            "close_but_different": [
                "How do I use AWS Secrets Manager to store and retrieve environment variables for a Python application?",
                "How do I manage environment variables for a Node.js application across development and production?",
                "How do I validate that all required environment variables are set when a Python application starts?",
            ],
            "unrelated": [
                "How do I write a Python script to rename all files in a directory by adding a timestamp prefix?"
            ],
        },
    },
    {
        "id": "structured_logging",
        "domain": "devops",
        "base_prompt": "How do I set up structured JSON logging in a Python application for production use?",
        "variants": {
            "exact_duplicate": [
                "How do I set up structured JSON logging in a Python application for production use?"
            ],
            "paraphrase": [
                "Show me how to configure Python's logging module to output JSON-formatted log lines",
                "How can I make my Python app emit structured logs that can be parsed by log aggregators?",
                "Give me Python code that sets up a JSON log formatter for structured production logging",
                "Implement structured logging in Python so every log line is a valid JSON object with standard fields",
                "What is the recommended approach for structured JSON logging in a Python service?",
            ],
            "close_but_different": [
                "How do I set up rotating file logging in Python so log files don't grow unboundedly?",
                "How do I forward Python application logs to a centralized logging service like Datadog or Splunk?",
                "How do I add request-scoped context (like a trace ID) to all log lines in a Python web app?",
            ],
            "unrelated": [
                "How do I use SQLAlchemy to define a self-referential many-to-many relationship?"
            ],
        },
    },
    {
        "id": "kubernetes_deployment_yaml",
        "domain": "devops",
        "base_prompt": "Write a Kubernetes Deployment manifest for a Python web application with 3 replicas",
        "variants": {
            "exact_duplicate": [
                "Write a Kubernetes Deployment manifest for a Python web application with 3 replicas"
            ],
            "paraphrase": [
                "How do I write a Kubernetes Deployment YAML to run my Python app with three replicas?",
                "Give me a k8s Deployment spec that deploys 3 pods running a Python web service",
                "Create a Kubernetes Deployment manifest that runs a containerized Python application at 3 instances",
                "Show me the YAML for a Kubernetes Deployment of a Python app with replica count set to 3",
                "What should a Kubernetes Deployment manifest look like for a Python web service with 3 replicas?",
            ],
            "close_but_different": [
                "Write a Kubernetes StatefulSet manifest for a Python application that needs persistent storage",
                "Write a Kubernetes Deployment manifest for a Python web application with autoscaling configured",
                "Write a Kubernetes Service manifest to expose a Python web application Deployment via a LoadBalancer",
            ],
            "unrelated": [
                "How do I implement rate limiting in Python using a sliding window counter?"
            ],
        },
    },
    {
        "id": "shell_script_backup",
        "domain": "devops",
        "base_prompt": "Write a bash shell script to back up a PostgreSQL database and upload it to S3",
        "variants": {
            "exact_duplicate": [
                "Write a bash shell script to back up a PostgreSQL database and upload it to S3"
            ],
            "paraphrase": [
                "How do I automate PostgreSQL database backups and send them to an S3 bucket using bash?",
                "Give me a shell script that runs pg_dump and copies the resulting file to AWS S3",
                "Create a bash script that dumps a Postgres database to a file and syncs it to S3",
                "Show me a cron-friendly bash script that backs up Postgres with pg_dump and uploads to S3",
                "What should a bash script look like to schedule regular PostgreSQL backups to S3?",
            ],
            "close_but_different": [
                "Write a bash script to back up a MySQL database and upload it to S3",
                "Write a bash script to back up a PostgreSQL database and store it locally with a retention policy",
                "Write a bash script to restore a PostgreSQL database from an S3 backup file",
            ],
            "unrelated": [
                "How do I write a Python function to validate a credit card number using the Luhn algorithm?"
            ],
        },
    },
    {
        "id": "health_check_endpoint",
        "domain": "devops",
        "base_prompt": "How do I implement a health check endpoint in a FastAPI application for Kubernetes liveness and readiness probes?",
        "variants": {
            "exact_duplicate": [
                "How do I implement a health check endpoint in a FastAPI application for Kubernetes liveness and readiness probes?"
            ],
            "paraphrase": [
                "Show me how to add /healthz and /readyz endpoints to a FastAPI service for k8s probes",
                "How can I expose a health check route in FastAPI that verifies the app and its dependencies are up?",
                "Give me FastAPI code for liveness and readiness probe endpoints that Kubernetes can poll",
                "Implement a FastAPI health check endpoint that returns 200 OK when the service is healthy",
                "What is the right way to set up health check routes in FastAPI for Kubernetes monitoring?",
            ],
            "close_but_different": [
                "How do I implement a health check endpoint in a Flask application for load balancer health checks?",
                "How do I add Prometheus metrics scraping to a FastAPI application for observability?",
                "How do I configure Kubernetes readiness probes to wait for a database connection before routing traffic?",
            ],
            "unrelated": [
                "How do I use Python's functools.partial to create a pre-configured version of a function?"
            ],
        },
    },
    # ================================================================
    # ml_data_science (10 groups)
    # ================================================================
    {
        "id": "pandas_groupby_agg",
        "domain": "ml_data_science",
        "base_prompt": "How do I group a pandas DataFrame by a column and compute aggregate statistics for each group?",
        "variants": {
            "exact_duplicate": [
                "How do I group a pandas DataFrame by a column and compute aggregate statistics for each group?"
            ],
            "paraphrase": [
                "Show me how to use pandas groupby to calculate mean, sum, and count per group",
                "How can I aggregate a DataFrame in pandas by a categorical column and get summary stats?",
                "Give me pandas code that groups rows by a column value and computes multiple aggregations",
                "Implement pandas groupby aggregation to get the total and average per category in a DataFrame",
                "What is the pandas way to split a DataFrame into groups and calculate statistics for each?",
            ],
            "close_but_different": [
                "How do I group a pandas DataFrame by multiple columns and compute aggregate statistics?",
                "How do I apply a custom aggregation function to grouped data in pandas?",
                "How do I use pandas pivot_table to compute aggregations across row and column groupings?",
            ],
            "unrelated": [
                "How do I implement a circular buffer in Python using a deque?"
            ],
        },
    },
    {
        "id": "pandas_merge_join",
        "domain": "ml_data_science",
        "base_prompt": "How do I merge two pandas DataFrames on a common column using an inner join?",
        "variants": {
            "exact_duplicate": [
                "How do I merge two pandas DataFrames on a common column using an inner join?"
            ],
            "paraphrase": [
                "Show me how to join two pandas DataFrames on a shared key column",
                "How can I use pd.merge to combine two DataFrames like an SQL inner join?",
                "Give me pandas code that merges two tables on a matching column and keeps only common rows",
                "Implement a pandas inner join between two DataFrames on a user_id column",
                "What is the pandas equivalent of SQL INNER JOIN on a common key?",
            ],
            "close_but_different": [
                "How do I merge two pandas DataFrames on a common column using a left join?",
                "How do I concatenate two pandas DataFrames vertically using pd.concat?",
                "How do I merge two pandas DataFrames on multiple columns using an outer join?",
            ],
            "unrelated": [
                "How do I create a Flask route that returns a paginated JSON response?"
            ],
        },
    },
    {
        "id": "numpy_matrix_operations",
        "domain": "ml_data_science",
        "base_prompt": "How do I perform matrix multiplication and compute the inverse of a matrix using NumPy?",
        "variants": {
            "exact_duplicate": [
                "How do I perform matrix multiplication and compute the inverse of a matrix using NumPy?"
            ],
            "paraphrase": [
                "Show me NumPy code to multiply two matrices and find the inverse of a square matrix",
                "How can I do matrix math in Python — specifically matrix multiplication and inversion — with NumPy?",
                "Give me numpy operations to multiply two 2D arrays and compute the matrix inverse",
                "Implement matrix multiplication using np.dot or @ and find the inverse with np.linalg.inv",
                "What NumPy functions do I use to multiply matrices and invert a matrix in Python?",
            ],
            "close_but_different": [
                "How do I compute eigenvalues and eigenvectors of a matrix using NumPy?",
                "How do I perform element-wise multiplication of two NumPy arrays?",
                "How do I compute the dot product of two vectors and the cross product using NumPy?",
            ],
            "unrelated": [
                "How do I write an asyncio coroutine that streams HTTP responses using httpx?"
            ],
        },
    },
    {
        "id": "sklearn_train_test_split",
        "domain": "ml_data_science",
        "base_prompt": "How do I split a dataset into training and test sets using scikit-learn's train_test_split?",
        "variants": {
            "exact_duplicate": [
                "How do I split a dataset into training and test sets using scikit-learn's train_test_split?"
            ],
            "paraphrase": [
                "Show me how to use sklearn's train_test_split to divide features and labels for ML",
                "How can I create train and test splits from a pandas DataFrame using scikit-learn?",
                "Give me sklearn code to split X and y into training and test sets with a fixed random seed",
                "Implement a dataset split in scikit-learn reserving 20% for testing and 80% for training",
                "What is the standard way to split features and target into train and test sets with sklearn?",
            ],
            "close_but_different": [
                "How do I split a dataset into training, validation, and test sets using scikit-learn?",
                "How do I perform stratified train-test splitting in scikit-learn to preserve class distribution?",
                "How do I use scikit-learn's KFold to split data into K cross-validation folds?",
            ],
            "unrelated": [
                "How do I use Python's subprocess to run a command and capture both stdout and stderr?"
            ],
        },
    },
    {
        "id": "pandas_missing_values",
        "domain": "ml_data_science",
        "base_prompt": "How do I detect and handle missing values in a pandas DataFrame?",
        "variants": {
            "exact_duplicate": [
                "How do I detect and handle missing values in a pandas DataFrame?"
            ],
            "paraphrase": [
                "Show me how to find NaN values in a pandas DataFrame and fill or drop them",
                "How can I check for missing data in a pandas DataFrame and decide how to clean it?",
                "Give me pandas code to identify null values in each column and impute or remove them",
                "Implement missing value handling in pandas — detect, fill with mean, and drop remaining nulls",
                "What are the pandas methods for finding and dealing with NaN values in a DataFrame?",
            ],
            "close_but_different": [
                "How do I detect and handle outliers in a pandas DataFrame using IQR?",
                "How do I fill missing values in a pandas time series using forward fill?",
                "How do I use scikit-learn's SimpleImputer to fill missing values as part of a pipeline?",
            ],
            "unrelated": [
                "How do I write a bash script that monitors disk usage and sends an alert when it exceeds 80%?"
            ],
        },
    },
    {
        "id": "sklearn_logistic_regression",
        "domain": "ml_data_science",
        "base_prompt": "How do I train a logistic regression model in scikit-learn and evaluate it on a test set?",
        "variants": {
            "exact_duplicate": [
                "How do I train a logistic regression model in scikit-learn and evaluate it on a test set?"
            ],
            "paraphrase": [
                "Show me how to fit a LogisticRegression classifier in sklearn and measure its accuracy",
                "How can I build and evaluate a logistic regression model using scikit-learn?",
                "Give me sklearn code to train a logistic regression, predict on test data, and print accuracy",
                "Implement binary classification with scikit-learn's LogisticRegression and evaluate with classification_report",
                "What is the sklearn workflow for training logistic regression and checking model performance?",
            ],
            "close_but_different": [
                "How do I train a random forest classifier in scikit-learn and evaluate it on a test set?",
                "How do I train a linear regression model in scikit-learn and evaluate with RMSE?",
                "How do I tune the regularization hyperparameter of logistic regression using GridSearchCV in sklearn?",
            ],
            "unrelated": [
                "How do I write a Click CLI that reads from multiple input files and merges the results?"
            ],
        },
    },
    {
        "id": "matplotlib_line_plot",
        "domain": "ml_data_science",
        "base_prompt": "How do I create a line plot with multiple series, a legend, and axis labels using matplotlib?",
        "variants": {
            "exact_duplicate": [
                "How do I create a line plot with multiple series, a legend, and axis labels using matplotlib?"
            ],
            "paraphrase": [
                "Show me how to plot multiple lines on the same matplotlib figure with a legend and labeled axes",
                "How can I use matplotlib to draw a multi-series line chart with proper labels and a legend?",
                "Give me matplotlib code that plots two lines on one axes, adds x/y labels, and shows a legend",
                "Implement a matplotlib line chart with multiple data series, axis titles, and a legend",
                "What matplotlib calls do I need to create a multi-line plot with labels and a legend?",
            ],
            "close_but_different": [
                "How do I create a bar chart with multiple groups and a legend using matplotlib?",
                "How do I create a scatter plot with color-coded points and a color bar using matplotlib?",
                "How do I add a secondary y-axis to a matplotlib line plot for two different scales?",
            ],
            "unrelated": [
                "How do I configure Alembic to use an async SQLAlchemy engine for migrations?"
            ],
        },
    },
    {
        "id": "feature_engineering_pipeline",
        "domain": "ml_data_science",
        "base_prompt": "How do I build a scikit-learn pipeline that scales numeric features and one-hot encodes categorical features?",
        "variants": {
            "exact_duplicate": [
                "How do I build a scikit-learn pipeline that scales numeric features and one-hot encodes categorical features?"
            ],
            "paraphrase": [
                "Show me a sklearn Pipeline with StandardScaler for numerics and OneHotEncoder for categoricals",
                "How can I preprocess a mixed dataset in sklearn with separate transformers for numeric and categorical columns?",
                "Give me sklearn code using ColumnTransformer to apply scaling and one-hot encoding in one pipeline",
                "Implement a scikit-learn preprocessing pipeline that normalizes numbers and encodes categories",
                "What is the sklearn way to combine StandardScaler and OneHotEncoder in a ColumnTransformer pipeline?",
            ],
            "close_but_different": [
                "How do I build a scikit-learn pipeline that scales features and then applies PCA for dimensionality reduction?",
                "How do I build a scikit-learn pipeline that imputes missing values and then trains a random forest?",
                "How do I apply target encoding for high-cardinality categorical features in a sklearn pipeline?",
            ],
            "unrelated": [
                "How do I write a Python decorator that measures and logs a function's execution time?"
            ],
        },
    },
    {
        "id": "cross_validation",
        "domain": "ml_data_science",
        "base_prompt": "How do I use k-fold cross-validation in scikit-learn to evaluate a model's generalization performance?",
        "variants": {
            "exact_duplicate": [
                "How do I use k-fold cross-validation in scikit-learn to evaluate a model's generalization performance?"
            ],
            "paraphrase": [
                "Show me how to use sklearn's cross_val_score to perform 5-fold cross-validation",
                "How can I evaluate a scikit-learn classifier using k-fold CV instead of a single train-test split?",
                "Give me sklearn code that performs cross-validation and reports mean and std of accuracy across folds",
                "Implement k-fold cross-validation in scikit-learn using cross_validate for multiple metrics",
                "What is the sklearn API for running k-fold cross-validation and getting per-fold scores?",
            ],
            "close_but_different": [
                "How do I use stratified k-fold cross-validation in scikit-learn to preserve class balance?",
                "How do I use leave-one-out cross-validation in scikit-learn for a small dataset?",
                "How do I use GridSearchCV in scikit-learn to tune hyperparameters with cross-validation?",
            ],
            "unrelated": [
                "How do I implement a thread-safe counter in Python using threading.Lock?"
            ],
        },
    },
    {
        "id": "pandas_read_parquet",
        "domain": "ml_data_science",
        "base_prompt": "How do I read a Parquet file into a pandas DataFrame and filter rows efficiently?",
        "variants": {
            "exact_duplicate": [
                "How do I read a Parquet file into a pandas DataFrame and filter rows efficiently?"
            ],
            "paraphrase": [
                "Show me how to load a .parquet file with pandas and apply a row filter",
                "How can I use pd.read_parquet to load data from a Parquet file and select specific rows?",
                "Give me pandas code to read a Parquet dataset and filter to rows where a column meets a condition",
                "Implement efficient Parquet file reading in pandas using column selection and predicate pushdown",
                "What is the pandas way to read a Parquet file and filter rows without loading everything into memory?",
            ],
            "close_but_different": [
                "How do I write a pandas DataFrame to a Parquet file with snappy compression?",
                "How do I read a CSV file into a pandas DataFrame and filter rows efficiently?",
                "How do I read a Parquet file into a polars DataFrame and filter rows efficiently?",
            ],
            "unrelated": [
                "How do I configure Nginx to serve static files with caching headers?"
            ],
        },
    },
    # ================================================================
    # 16 additional groups — 2 per existing domain
    # ================================================================
    # ---- data_structures (2) ----
    {
        "id": "heap_kth_largest",
        "domain": "data_structures",
        "base_prompt": "Write a Python function to find the k-th largest element in a list using a min-heap",
        "variants": {
            "exact_duplicate": [
                "Write a Python function to find the k-th largest element in a list using a min-heap"
            ],
            "paraphrase": [
                "How do I get the k-th largest number from a list efficiently using a heap in Python?",
                "Implement kth largest element in Python using heapq with a min-heap of size k",
                "Give me Python code that uses a min-heap to find the k-th biggest value in an unsorted list",
                "Find the k-th largest element in a Python list using the heapq module",
                "Write a heap-based Python function that returns the element at rank k from the largest in a list",
            ],
            "close_but_different": [
                "Write a Python function to find the k-th smallest element in a list using a min-heap",
                "Write a Python function to return the top-k largest elements from a list using a heap",
                "Write a Python function to find the median of a list using two heaps",
            ],
            "unrelated": [
                "How do I use GitHub Actions to deploy a Python app to AWS Elastic Beanstalk?"
            ],
        },
    },
    {
        "id": "graph_topological_sort",
        "domain": "data_structures",
        "base_prompt": "Write a Python function to perform topological sort on a directed acyclic graph using DFS",
        "variants": {
            "exact_duplicate": [
                "Write a Python function to perform topological sort on a directed acyclic graph using DFS"
            ],
            "paraphrase": [
                "How do I topologically order the nodes of a DAG in Python using depth-first search?",
                "Implement topological sorting for a directed graph in Python using a DFS-based approach",
                "Give me Python code to sort graph nodes in topological order using recursive DFS",
                "Write a DFS-based topological sort algorithm in Python for a directed acyclic graph",
                "Implement Tarjan's algorithm for topological ordering of a DAG in Python",
            ],
            "close_but_different": [
                "Write a Python function to perform topological sort on a DAG using Kahn's BFS-based algorithm",
                "Write a Python function to detect a cycle in a directed graph using DFS",
                "Write a Python function to find the shortest path in a DAG using dynamic programming",
            ],
            "unrelated": [
                "How do I configure pandas to display more columns and rows without truncation?"
            ],
        },
    },
    # ---- api_development (2) ----
    {
        "id": "fastapi_file_upload",
        "domain": "api_development",
        "base_prompt": "How do I create a FastAPI endpoint that accepts file uploads and saves them to disk?",
        "variants": {
            "exact_duplicate": [
                "How do I create a FastAPI endpoint that accepts file uploads and saves them to disk?"
            ],
            "paraphrase": [
                "Show me how to handle multipart file uploads in FastAPI and persist the file",
                "How can I receive uploaded files in a FastAPI POST endpoint and write them to a directory?",
                "Give me FastAPI code for an endpoint that accepts an UploadFile and saves it locally",
                "Implement a FastAPI route that handles file upload and stores the file on the server",
                "What does a FastAPI endpoint look like that accepts a file via multipart form and saves it?",
            ],
            "close_but_different": [
                "How do I create a FastAPI endpoint that accepts file uploads and stores them in S3?",
                "How do I create a FastAPI endpoint that accepts multiple file uploads at once?",
                "How do I create a Flask endpoint that accepts file uploads and validates the file type?",
            ],
            "unrelated": [
                "How do I normalize a numpy array to the range [0, 1]?"
            ],
        },
    },
    {
        "id": "openapi_custom_docs",
        "domain": "api_development",
        "base_prompt": "How do I customize the OpenAPI schema and Swagger UI metadata in a FastAPI application?",
        "variants": {
            "exact_duplicate": [
                "How do I customize the OpenAPI schema and Swagger UI metadata in a FastAPI application?"
            ],
            "paraphrase": [
                "Show me how to set a custom title, description, and version in FastAPI's OpenAPI docs",
                "How can I add API metadata like contact info and license to FastAPI's auto-generated OpenAPI spec?",
                "Give me FastAPI code to customize the /docs Swagger UI with a logo, title, and description",
                "Implement custom OpenAPI metadata in FastAPI including tags, descriptions, and external docs links",
                "What FastAPI parameters do I pass to set a custom title and description in the generated docs?",
            ],
            "close_but_different": [
                "How do I hide specific FastAPI endpoints from the auto-generated OpenAPI documentation?",
                "How do I add custom response examples to FastAPI endpoint OpenAPI docs?",
                "How do I generate an OpenAPI spec from a Flask application using flask-smorest?",
            ],
            "unrelated": [
                "How do I compute pairwise cosine similarity between sentence embeddings using numpy?"
            ],
        },
    },
    # ---- file_io (2) ----
    {
        "id": "read_yaml_config",
        "domain": "file_io",
        "base_prompt": "How do I read and parse a YAML configuration file in Python using PyYAML?",
        "variants": {
            "exact_duplicate": [
                "How do I read and parse a YAML configuration file in Python using PyYAML?"
            ],
            "paraphrase": [
                "Show me how to load a .yaml file into a Python dict using the yaml module",
                "How can I use PyYAML to parse a YAML config file and access nested keys?",
                "Give me Python code to open a YAML file and load its contents as a Python dictionary",
                "Implement YAML config file loading in Python using yaml.safe_load",
                "What is the correct way to read a YAML configuration file in Python with PyYAML?",
            ],
            "close_but_different": [
                "How do I read and parse a TOML configuration file in Python using tomllib?",
                "How do I write a Python dictionary to a YAML file using PyYAML?",
                "How do I validate a YAML configuration file against a schema using Python's jsonschema library?",
            ],
            "unrelated": [
                "How do I use scikit-learn to compute feature importance from a random forest classifier?"
            ],
        },
    },
    {
        "id": "tail_log_file",
        "domain": "file_io",
        "base_prompt": "How do I continuously read new lines appended to a log file in Python, similar to tail -f?",
        "variants": {
            "exact_duplicate": [
                "How do I continuously read new lines appended to a log file in Python, similar to tail -f?"
            ],
            "paraphrase": [
                "Show me Python code that follows a log file and prints new lines as they are written",
                "How can I implement a tail -f style log follower in Python that streams new log entries?",
                "Give me Python code that monitors a file and yields each new line as it is appended",
                "Implement a log file tailer in Python that sleeps and re-reads a file when new data arrives",
                "Write a Python generator that continuously follows a growing log file line by line",
            ],
            "close_but_different": [
                "How do I read the last N lines from a log file efficiently in Python without reading the whole file?",
                "How do I continuously read messages from a Unix named pipe (FIFO) in Python?",
                "How do I watch a log file for lines matching a pattern and alert when they appear in Python?",
            ],
            "unrelated": [
                "How do I use Kubernetes ConfigMaps to inject environment variables into a pod?"
            ],
        },
    },
    # ---- database (2) ----
    {
        "id": "redis_cache_aside",
        "domain": "database",
        "base_prompt": "How do I implement a cache-aside pattern in Python using Redis to cache database query results?",
        "variants": {
            "exact_duplicate": [
                "How do I implement a cache-aside pattern in Python using Redis to cache database query results?"
            ],
            "paraphrase": [
                "Show me how to use Redis as a cache in Python: check cache first, fall back to DB on miss",
                "How can I add Redis caching in front of a database query in Python to reduce DB load?",
                "Give me Python code that looks up a key in Redis, fetches from the database on miss, and stores it",
                "Implement the cache-aside caching strategy in Python: Redis lookup, DB fallback, cache write",
                "What is the Python pattern for caching DB results in Redis with a TTL?",
            ],
            "close_but_different": [
                "How do I implement a write-through cache pattern in Python using Redis?",
                "How do I use Redis pub/sub in Python to broadcast messages to multiple subscribers?",
                "How do I use Redis as a distributed lock in Python to prevent concurrent access?",
            ],
            "unrelated": [
                "How do I use matplotlib to create a heatmap from a 2D numpy array?"
            ],
        },
    },
    {
        "id": "db_connection_pooling",
        "domain": "database",
        "base_prompt": "How do I configure SQLAlchemy's connection pool size and timeout for a production application?",
        "variants": {
            "exact_duplicate": [
                "How do I configure SQLAlchemy's connection pool size and timeout for a production application?"
            ],
            "paraphrase": [
                "Show me how to set pool_size, max_overflow, and pool_timeout in SQLAlchemy for production",
                "How can I tune SQLAlchemy's connection pool parameters to handle high traffic in production?",
                "Give me SQLAlchemy create_engine configuration options for controlling connection pool behavior",
                "Implement SQLAlchemy connection pooling with a fixed pool size and connection recycle timeout",
                "What SQLAlchemy engine options should I set for a production-grade connection pool configuration?",
            ],
            "close_but_different": [
                "How do I configure SQLAlchemy to use NullPool to disable connection pooling for serverless functions?",
                "How do I configure asyncpg's connection pool size and max connections for a production application?",
                "How do I monitor and log SQLAlchemy connection pool events for debugging connection issues?",
            ],
            "unrelated": [
                "How do I use Python's multiprocessing module to parallelize CPU-intensive tasks?"
            ],
        },
    },
    # ---- async_programming (2) ----
    {
        "id": "asyncio_subprocess",
        "domain": "async_programming",
        "base_prompt": "How do I run a shell command asynchronously in Python using asyncio.create_subprocess_exec?",
        "variants": {
            "exact_duplicate": [
                "How do I run a shell command asynchronously in Python using asyncio.create_subprocess_exec?"
            ],
            "paraphrase": [
                "Show me how to execute a subprocess without blocking the asyncio event loop in Python",
                "How can I run an external command in Python asyncio and capture its stdout?",
                "Give me asyncio code to launch a subprocess and read its output asynchronously",
                "Implement async subprocess execution in Python using asyncio.create_subprocess_exec",
                "What is the asyncio way to spawn a child process and await its output in Python?",
            ],
            "close_but_different": [
                "How do I run a shell command synchronously in Python using subprocess.run and capture output?",
                "How do I stream stdout lines from an asyncio subprocess in real time as they are produced?",
                "How do I run multiple shell commands in parallel using asyncio subprocesses in Python?",
            ],
            "unrelated": [
                "How do I use pandas to resample a time series DataFrame to a weekly frequency and fill gaps?"
            ],
        },
    },
    {
        "id": "asyncio_retry_backoff",
        "domain": "async_programming",
        "base_prompt": "How do I implement exponential backoff retry logic for an asyncio coroutine that may fail transiently?",
        "variants": {
            "exact_duplicate": [
                "How do I implement exponential backoff retry logic for an asyncio coroutine that may fail transiently?"
            ],
            "paraphrase": [
                "Show me how to retry a failing asyncio coroutine with exponential delays in Python",
                "How can I add automatic retry with exponential backoff to an async function in Python?",
                "Give me asyncio Python code that retries a coroutine up to N times with increasing wait intervals",
                "Implement an async retry decorator in Python that uses exponential backoff for transient errors",
                "What is the pattern for retrying an asyncio coroutine with jittered exponential backoff?",
            ],
            "close_but_different": [
                "How do I implement exponential backoff retry logic for a synchronous function using tenacity?",
                "How do I implement a circuit breaker that stops retrying after too many failures in asyncio?",
                "How do I use the tenacity library to add retry logic to an async function in Python?",
            ],
            "unrelated": [
                "How do I write a Terraform module to create a reusable VPC configuration on AWS?"
            ],
        },
    },
    # ---- testing (2) ----
    {
        "id": "pytest_coverage",
        "domain": "testing",
        "base_prompt": "How do I measure code coverage with pytest-cov and enforce a minimum coverage threshold?",
        "variants": {
            "exact_duplicate": [
                "How do I measure code coverage with pytest-cov and enforce a minimum coverage threshold?"
            ],
            "paraphrase": [
                "Show me how to run pytest with coverage reporting using pytest-cov",
                "How can I set up pytest-cov to generate a coverage report and fail the build if coverage drops below 80%?",
                "Give me the pytest command and configuration to measure test coverage and enforce a minimum percentage",
                "Implement coverage measurement in a Python project using pytest-cov with a required threshold",
                "What pytest-cov configuration options do I need to measure coverage and set a minimum threshold?",
            ],
            "close_but_different": [
                "How do I generate an HTML coverage report with pytest-cov for visual inspection?",
                "How do I exclude specific files and directories from pytest-cov coverage measurement?",
                "How do I run coverage.py directly (without pytest-cov) and generate an XML report for CI?",
            ],
            "unrelated": [
                "How do I use pandas to detect and remove duplicate rows from a DataFrame?"
            ],
        },
    },
    {
        "id": "pytest_database_fixture",
        "domain": "testing",
        "base_prompt": "How do I write a pytest fixture that creates a test database, runs migrations, and tears it down after tests?",
        "variants": {
            "exact_duplicate": [
                "How do I write a pytest fixture that creates a test database, runs migrations, and tears it down after tests?"
            ],
            "paraphrase": [
                "Show me a pytest fixture that sets up a SQLAlchemy database with tables and cleans up afterward",
                "How can I create a pytest fixture that initializes a test database with Alembic and drops it after the suite?",
                "Give me a pytest conftest.py fixture that provisions a test database, seeds it, and tears it down",
                "Implement a session-scoped pytest fixture that creates a database, applies schema, and destroys it after all tests",
                "What is the pattern for a pytest fixture that manages full database lifecycle for integration tests?",
            ],
            "close_but_different": [
                "How do I write a pytest fixture that wraps each test in a database transaction and rolls it back?",
                "How do I write a pytest fixture that clears all database tables between tests without dropping them?",
                "How do I use pytest-django's database fixture to run Django model tests with automatic rollback?",
            ],
            "unrelated": [
                "How do I write a Kubernetes CronJob manifest to run a Python batch script on a schedule?"
            ],
        },
    },
    # ---- cli_tools (2) ----
    {
        "id": "click_testing_clirunner",
        "domain": "cli_tools",
        "base_prompt": "How do I test a Click CLI command in pytest using Click's CliRunner?",
        "variants": {
            "exact_duplicate": [
                "How do I test a Click CLI command in pytest using Click's CliRunner?"
            ],
            "paraphrase": [
                "Show me how to use Click's CliRunner to invoke a CLI command and assert its output in a test",
                "How can I write a pytest test for a Click command using the CliRunner without spawning a subprocess?",
                "Give me a pytest test that uses CliRunner to call a Click command and check the exit code and output",
                "Implement a unit test for a Click CLI using CliRunner to simulate command invocation",
                "What is the Click testing API for invoking commands in pytest without running a real subprocess?",
            ],
            "close_but_different": [
                "How do I test an argparse CLI in pytest by calling the main function with sys.argv patched?",
                "How do I test a Click command's stdin input using CliRunner's input parameter?",
                "How do I test a Click CLI command that writes files to disk using a temporary directory in pytest?",
            ],
            "unrelated": [
                "How do I use scikit-learn's GridSearchCV to tune a random forest classifier's hyperparameters?"
            ],
        },
    },
    {
        "id": "cli_shell_completion",
        "domain": "cli_tools",
        "base_prompt": "How do I add shell tab completion to a Python CLI built with Click?",
        "variants": {
            "exact_duplicate": [
                "How do I add shell tab completion to a Python CLI built with Click?"
            ],
            "paraphrase": [
                "Show me how to enable bash and zsh tab completion for a Click CLI command",
                "How can I set up shell autocompletion for my Click-based Python CLI tool?",
                "Give me the steps to activate tab completion for a Click CLI in bash and zsh",
                "Implement shell completion for a Click CLI so options and arguments are autocompleted",
                "What is the Click way to install shell completion scripts for bash, zsh, and fish?",
            ],
            "close_but_different": [
                "How do I add shell tab completion to a Python CLI built with argparse?",
                "How do I add dynamic tab completion that suggests values from a database to a Click CLI?",
                "How do I add shell tab completion to a Python CLI built with Typer?",
            ],
            "unrelated": [
                "How do I use Redis sorted sets to implement a leaderboard in Python?"
            ],
        },
    },
    # ---- string_manipulation (2) ----
    {
        "id": "string_slugify",
        "domain": "string_manipulation",
        "base_prompt": "Write a Python function to convert a string to a URL-friendly slug",
        "variants": {
            "exact_duplicate": [
                "Write a Python function to convert a string to a URL-friendly slug"
            ],
            "paraphrase": [
                "How do I create a URL slug from a title string in Python?",
                "Give me Python code that converts a headline to a hyphenated lowercase URL slug",
                "Implement a slugify function in Python that lowercases text and replaces spaces and special chars with hyphens",
                "Write a Python function that turns 'Hello World!' into 'hello-world' for use in a URL",
                "Show me a Python slugify implementation that strips accents and removes non-alphanumeric characters",
            ],
            "close_but_different": [
                "Write a Python function to convert a string to a filename-safe version by replacing special characters",
                "Write a Python function to convert a slug back to a human-readable title string",
                "Write a Python function to generate a URL-friendly slug that includes a numeric suffix to avoid duplicates",
            ],
            "unrelated": [
                "How do I configure a GitHub Actions workflow to cache pip dependencies between runs?"
            ],
        },
    },
    {
        "id": "string_parse_csv_line",
        "domain": "string_manipulation",
        "base_prompt": "Write a Python function to parse a single CSV line correctly handling quoted fields with embedded commas",
        "variants": {
            "exact_duplicate": [
                "Write a Python function to parse a single CSV line correctly handling quoted fields with embedded commas"
            ],
            "paraphrase": [
                "How do I split a CSV row in Python while respecting quoted fields that contain commas?",
                "Give me Python code that parses one line of CSV including fields quoted with double quotes",
                "Implement a CSV line parser in Python that handles embedded commas inside quoted values",
                "Write a Python function to tokenize a CSV string where fields may contain commas inside quotes",
                "Show me how to correctly split a single CSV line in Python without using the csv module",
            ],
            "close_but_different": [
                "Write a Python function to parse a TSV (tab-separated) line into a list of fields",
                "Write a Python function to serialize a list of strings to a properly escaped CSV line",
                "Write a Python function to parse a CSV line that uses a semicolon as the delimiter",
            ],
            "unrelated": [
                "How do I use asyncio.StreamReader to read data from a TCP socket in Python?"
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# MAIN EXPANSION LOGIC
# ---------------------------------------------------------------------------

def expand_dataset() -> None:
    input_path = os.path.join(
        os.path.dirname(__file__), "test_prompts.json"
    )
    with open(input_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    groups: list[dict] = data["prompt_groups"]

    # 1. Expand existing 64 groups
    expanded_count = 0
    for group in groups:
        gid = group["id"]
        if gid not in EXTRA_VARIANTS:
            print(f"  WARNING: no extra variants defined for '{gid}' — skipping")
            continue

        extras = EXTRA_VARIANTS[gid]
        group["variants"]["paraphrase"].extend(extras["paraphrase"])
        group["variants"]["close_but_different"].extend(extras["close_but_different"])
        expanded_count += 1

    print(f"Expanded {expanded_count} existing groups.")

    # 2. Append the 36 new groups
    groups.extend(NEW_GROUPS)
    print(f"Added {len(NEW_GROUPS)} new groups.")

    data["prompt_groups"] = groups

    # 3. Write back
    with open(input_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {len(groups)} total groups to {input_path}")

    # 4. Verify
    print("\n--- Verification ---")
    print(f"Total groups: {len(groups)}")
    from collections import Counter
    domain_counts: Counter = Counter(g["domain"] for g in groups)
    for domain, cnt in sorted(domain_counts.items()):
        print(f"  {domain}: {cnt} groups")

    print("\nVariant counts per group (sample + outliers):")
    issues = []
    for group in groups:
        v = group["variants"]
        ed = len(v["exact_duplicate"])
        para = len(v["paraphrase"])
        cbd = len(v["close_but_different"])
        unrel = len(v["unrelated"])
        total = ed + para + cbd + unrel
        if ed != 1 or para != 5 or cbd != 3 or unrel != 1:
            issues.append(
                f"  MISMATCH '{group['id']}': "
                f"exact={ed} para={para} close={cbd} unrelated={unrel} total={total}"
            )
    if issues:
        print("Issues found:")
        for issue in issues:
            print(issue)
    else:
        print("  All groups have: 1 exact_duplicate, 5 paraphrases, 3 close_but_different, 1 unrelated (total=10). OK!")


if __name__ == "__main__":
    expand_dataset()
