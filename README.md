# Deep Research (Python)

An AI-powered research assistant that performs iterative, deep research on any topic using search engines, web scraping, and large language models — now in **Python**.

> ⚡ **This project is a direct conversion of [@dzhng’s deep-research](https://github.com/dzhng/deep-research) from Node.js/TypeScript to Python.**

This is just a port of the original codebase into Python.  
The goal is to make the core logic easier for Python developers to read, run, and integrate into their own projects without the need for an API layer or backend setup.

> [!NOTE]  
> The `generate_text` function is introduced **only in this repo** and is exclusively for report generation in markdown format. Generating reports as JSON results in lower quality, while using markdown text directly yields better results.

## Features

- **Iterative Research**: Performs deep research by iteratively generating search queries, processing results, and diving deeper based on findings
- **Intelligent Query Generation**: Uses LLMs to generate targeted search queries based on research goals and previous findings
- **Depth & Breadth Control**: Configurable parameters to control how wide (breadth) and deep (depth) the research goes
- **Smart Follow-up**: Generates follow-up questions to better understand research needs
- **Comprehensive Reports**: Produces detailed markdown reports with findings and sources
- **Concurrent Processing**: Handles multiple searches and result processing in parallel for efficiency

## Requirements

- Python environment
- API keys for:
  - Firecrawl API (for web search and content extraction)
  - OpenAI API

## Setup

### Python

1. Clone the repository
2. Install dependencies using requirements.txt or using uv python:

```bash
pip install -r requirements.txt
```

**OR**

```bash
uv sync  # Only if you're using [uv](https://github.com/astral-sh/uv) as your Python package manager

```

3. Set up environment variables in a `.env` file:

```bash
FIRECRAWL_KEY="your_firecrawl_key"
# If you want to use your self-hosted Firecrawl, add the following below:
# FIRECRAWL_BASE_URL="http://localhost:3002"

OPENAI_KEY="your_openai_key"
```

To use Google Gemini, set the API key in `OPENAI_KEY` and the endpoint:

```bash
OPENAI_KEY="your_gemini_api_key"
OPENAI_ENDPOINT="https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL="gemini-2.0-flash-lite"
```


To use local LLM like ollama:

```bash
OPENAI_KEY=""
OPENAI_ENDPOINT="http://localhost:11434/v1"
MODEL="llama2"
```


## Usage

Run the research assistant:

```bash
python main.py
```

You'll be prompted to:

1. Enter your research query
2. Specify research breadth (recommended: 3-10, default: 4)
3. Specify research depth (recommended: 1-5, default: 2)
4. Answer follow-up questions to refine the research direction

The system will then:

1. Generate and execute search queries
2. Process and analyze search results
3. Recursively explore deeper based on findings
4. Generate a comprehensive markdown report

### Concurrency

If you have a paid version of Firecrawl or a local version, feel free to increase the `ConcurrencyLimit` by setting the `CONCURRENCY_LIMIT` environment variable so it runs faster.

If you have a free version, you may sometimes run into rate limit errors, you can reduce the limit to 1 (but it will run a lot slower).

## How It Works

1. **Initial Setup**

   - Takes user query and research parameters (breadth & depth)
   - Generates follow-up questions to understand research needs better

2. **Deep Research Process**

   - Generates multiple SERP queries based on research goals
   - Processes search results to extract key learnings
   - Generates follow-up research directions

3. **Recursive Exploration**

   - If depth > 0, takes new research directions and continues exploration
   - Each iteration builds on previous learnings
   - Maintains context of research goals and findings

4. **Report Generation**
   - Compiles all findings into a comprehensive markdown report
   - Includes all sources and references
   - Organizes information in a clear, readable format

## License

MIT License - feel free to use and modify as needed.
