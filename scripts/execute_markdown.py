
#!/usr/bin/env python3
"""Execute Markdown examples and generate documentation.

Conventions:
- sh/bash fences: execute with Bash, including multiline scripts.
- python fences: execute in a shared Python namespace.
- First text fence after an executable block: committed output
  snapshot, removed from generated documentation.
- Ordinary prose may separate code and its output snapshot.
- A heading or another fence ends the output association.
- Unlabelled and other language fences: preserved unchanged.
- No output comparisons or doctesting.

The source Markdown is never modified. Generated Markdown and
diagnostic logs are written to separate directories.
"""

import argparse
import contextlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

from markdown_it import MarkdownIt


EXECUTABLE_LANGUAGES = {"sh", "bash", "python"}


def text_fence(text: str) -> str:
    """Format captured output as a Markdown text fence."""
    if not text.strip():
        return ""

    # Use a fence longer than any backtick sequence in output.
    runs = re.findall(r"`+", text)
    marker = "`" * max(3, max(map(len, runs), default=0) + 1)

    return f"\n{marker}text\n{text.rstrip()}\n{marker}\n"


def execute_bash(
    code: str,
    workdir: Path,
    logfile: Path,
) -> str:
    """Execute a complete Bash block and stream output to logs."""
    chunks = []

    with logfile.open("w", encoding="utf-8") as log:
        with subprocess.Popen(
            ["bash", "-e", "-o", "pipefail", "-c", code],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as process:
            assert process.stdout is not None

            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
                chunks.append(line)

            status = process.wait()

    if status != 0:
        raise RuntimeError(
            f"Bash exited with status {status}; see {logfile}"
        )

    return "".join(chunks)


def execute_python(
    code: str,
    namespace: dict,
    logfile: Path,
    filename: str,
) -> str:
    """Execute Python with shared state and capture diagnostics."""
    captured = io.StringIO()

    try:
        with contextlib.redirect_stdout(captured):
            with contextlib.redirect_stderr(captured):
                exec(compile(code, filename, "exec"), namespace)

    except BaseException:
        captured.write(traceback.format_exc())
        output = captured.getvalue()

        logfile.write_text(output, encoding="utf-8")
        print(output, file=sys.stderr, flush=True)
        raise

    output = captured.getvalue()
    logfile.write_text(output, encoding="utf-8")

    if output:
        print(output, end="", flush=True)

    return output


def github_annotation(
    source: Path,
    line: int,
    message: str,
) -> None:
    """Emit a GitHub Actions error annotation for a source line."""
    def escape(value: str, property: bool = False) -> str:
        value = (
            str(value)
            .replace("%", "%25")
            .replace("\r", "%0D")
            .replace("\n", "%0A")
        )

        if property:
            value = (
                value.replace(":", "%3A")
                .replace(",", "%2C")
            )

        return value

    print(
        f"::error file={escape(source, True)},"
        f"line={line}::{escape(message)}",
        flush=True,
    )


def run(
    source: Path,
    output: Path,
    logs: Path,
) -> None:
    """Execute a Markdown file and render fresh output."""
    repository_root = Path.cwd().resolve()

    source = source.resolve()
    output = output.resolve()
    logs = logs.resolve()

    if source == output:
        raise ValueError("Output must differ from source")

    output.parent.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    # Execute in the original example directory.
    # BenchX needs the real Git checkout to record revision and
    # dirty-tree information correctly.
    workdir = source.parent

    original = source.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    tokens = MarkdownIt("commonmark").parse(original)

    # markdown-it-py identifies fences and headings.
    # Do not filter on token.level: valid fenced blocks may
    # have a nonzero nesting level.
    events = [
        token
        for token in tokens
        if token.map is not None
        and token.type in {"fence", "heading_open"}
    ]

    rendered = []
    cursor = 0
    awaiting_output = False
    block_number = 0

    # Python blocks share variables across the document.
    namespace = {"__name__": "__main__"}

    previous_cwd = Path.cwd()

    try:
        os.chdir(workdir)

        for token in events:
            start, end = token.map

            # Preserve all ordinary Markdown between events.
            rendered.extend(lines[cursor:start])

            if token.type == "heading_open":
                awaiting_output = False
                rendered.extend(lines[start:end])

            elif token.type == "fence":
                parts = token.info.strip().split()
                language = parts[0] if parts else ""

                executable = (
                    language in EXECUTABLE_LANGUAGES
                    and "noexec" not in parts[1:]
                )

                if language == "text" and awaiting_output:
                    # Remove the first committed text-output
                    # snapshot after an executable block.
                    #
                    # Ordinary prose may intervene, but a heading
                    # or another fence ends the association.
                    #
                    # Fresh output has already been inserted
                    # immediately after the executable block.
                    #
                    # We never compare committed and fresh output.
                    awaiting_output = False

                elif executable:
                    block_number += 1
                    line = start + 1
                    logfile = logs / f"block-{block_number:03d}.log"

                    # Preserve original code fence in rendered docs.
                    rendered.extend(lines[start:end])

                    print(
                        f"\n[{block_number}] "
                        f"{source}:{line} ({language})",
                        flush=True,
                    )

                    try:
                        if language in {"sh", "bash"}:
                            result = execute_bash(
                                token.content,
                                workdir,
                                logfile,
                            )
                        else:
                            result = execute_python(
                                token.content,
                                namespace,
                                logfile,
                                f"{source}:{line}",
                            )

                    except BaseException as exc:
                        try:
                            relative_source = (
                                source.relative_to(repository_root)
                            )
                        except ValueError:
                            relative_source = source

                        github_annotation(
                            relative_source,
                            line,
                            f"{language} block failed: {exc}",
                        )

                        print(
                            f"Failed block {block_number}. "
                            f"Diagnostics: {logfile}",
                            file=sys.stderr,
                        )
                        raise

                    # Insert fresh text output after executable code.
                    # Empty output does not produce a text fence.
                    rendered.append(text_fence(result))

                    awaiting_output = True

                else:
                    # Preserve unlabelled, json, yaml, noexec,
                    # and other non-executable fences unchanged.
                    rendered.extend(lines[start:end])
                    awaiting_output = False

            cursor = end

        rendered.extend(lines[cursor:])

        # CI must not pass if no examples were actually executed.
        if block_number == 0:
            raise RuntimeError(
                f"No executable blocks found in {source}. "
                "Expected sh, bash, or python fences."
            )

        # Write generated Markdown only after successful execution.
        output.write_text(
            "".join(rendered),
            encoding="utf-8",
        )

    finally:
        os.chdir(previous_cwd)

    print(f"\nGenerated documentation: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute Markdown examples and capture outputs"
    )

    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Source Markdown file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Generated Markdown file",
    )
    parser.add_argument(
        "--logs",
        type=Path,
        required=True,
        help="Directory for per-block diagnostic logs",
    )

    args = parser.parse_args()
    run(args.source, args.output, args.logs)


if __name__ == "__main__":
    main()

