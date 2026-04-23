import os
import subprocess

PROJECT_ROOT = "."

def list_project_files():
    collected = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "venv"}]

        for file in files:
            if file.endswith((".py", ".js", ".html", ".css", ".json", ".md", ".txt", ".cs")):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                collected.append(rel_path)

    if not collected:
        return "I could not find any project files."

    preview = collected[:25]
    return "Here are some project files: " + " ".join(f"{i+1}. {path}" for i, path in enumerate(preview))


def _read_file(file_path):
    if not os.path.exists(file_path):
        return None, f"I could not find the file {file_path}."

    if not os.path.isfile(file_path):
        return None, f"{file_path} is not a file."

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content, None
    except Exception as e:
        return None, f"I could not read {file_path}: {str(e)}"


def read_file_summary(file_path):
    content, error = _read_file(file_path)
    if error:
        return error

    lines = content.splitlines()
    line_count = len(lines)
    preview = "\n".join(lines[:20]).strip()

    if not preview:
        return f"{file_path} is empty."

    return (
        f"{file_path} has {line_count} lines. "
        f"Here is a preview of the beginning:\n{preview}"
    )


def analyze_file(file_path):
    content, error = _read_file(file_path)
    if error:
        return error

    lines = content.splitlines()
    line_count = len(lines)

    if line_count == 0:
        return f"{file_path} is empty."

    lower_name = file_path.lower()
    findings = []

    if lower_name.endswith(".py"):
        findings.append("This appears to be a Python file.")

        imports = [line.strip() for line in lines if line.strip().startswith("import ") or line.strip().startswith("from ")]
        functions = [line.strip() for line in lines if line.strip().startswith("def ")]
        classes = [line.strip() for line in lines if line.strip().startswith("class ")]

        if imports:
            findings.append("Imports: " + "; ".join(imports[:8]))
        if functions:
            findings.append("Functions: " + "; ".join(functions[:8]))
        if classes:
            findings.append("Classes: " + "; ".join(classes[:5]))

        if "@app.route" in content or "Blueprint(" in content:
            findings.append("This file likely defines backend API routes.")
        if "OpenAI(" in content or "client.responses.create" in content:
            findings.append("This file appears to use the OpenAI API.")
        if "jsonify" in content:
            findings.append("This file returns JSON responses.")
        if "os.walk" in content:
            findings.append("This file scans directories or project files.")

    elif lower_name.endswith(".js"):
        findings.append("This appears to be a JavaScript file.")
    elif lower_name.endswith(".html"):
        findings.append("This appears to be an HTML file.")
    elif lower_name.endswith(".css"):
        findings.append("This appears to be a CSS file.")
    elif lower_name.endswith(".json"):
        findings.append("This appears to be a JSON file.")
    elif lower_name.endswith(".cs"):
        findings.append("This appears to be a C# file, likely for Unity if used in your project.")

    preview = "\n".join(lines[:15]).strip()

    result = f"{file_path} has {line_count} lines. "
    if findings:
        result += " ".join(findings) + " "
    result += "Preview:\n" + preview

    return result


def read_log_file(file_path):
    content, error = _read_file(file_path)
    if error:
        return error

    lines = content.splitlines()

    if not lines:
        return f"{file_path} is empty."

    tail = "\n".join(lines[-20:]).strip()
    return f"Here are the latest log lines from {file_path}:\n{tail}"


def explain_error_text(error_text):
    text = (error_text or "").strip()

    if not text:
        return "Please give me an error message to explain."

    lowered = text.lower()

    if "connection refused" in lowered:
        return "That usually means your client tried to connect to a server that is not running or not listening on that port."

    if "modulenotfounderror" in lowered or "no module named" in lowered:
        return "That means Python cannot find a required package or module. Usually the package is not installed, the import path is wrong, or the wrong interpreter is selected."

    if "importerror" in lowered:
        return "That usually means Python found the package, but could not import the requested name. The file name, function name, or package structure may be wrong."

    if "500 internal server error" in lowered:
        return "That means the server crashed while handling the request. Check the backend logs or traceback for the real exception."

    return f"Here is my quick explanation of the error: {text}"


def summarize_backend():
    collected = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "venv"}]

        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                collected.append(rel_path)

    if not collected:
        return "I could not find any Python backend files."

    important = []
    for path in collected:
        lower = path.lower()
        if any(name in lower for name in ["app.py", "router", "dispatcher", "routes", "service"]):
            important.append(path)

    if not important:
        important = collected[:10]

    return (
        "This backend appears to be organized around Flask routes, service files, and execution handlers. "
        "Important files include: " +
        " ".join(f"{i+1}. {path}" for i, path in enumerate(important[:10]))
    )


def get_key_project_files():
    collected = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "venv"}]

        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                collected.append(rel_path)

    if not collected:
        return "I could not find any important project files."

    ranked = []
    priority_names = [
        "app.py",
        "voice_routes.py",
        "router_service.py",
        "dispatcher.py",
        "task_service.py",
        "memory_service.py",
        "dev_service.py"
    ]

    for name in priority_names:
        for path in collected:
            if path.endswith(name) and path not in ranked:
                ranked.append(path)

    for path in collected:
        if path not in ranked:
            ranked.append(path)

    preview = ranked[:10]
    return "The most important project files seem to be: " + " ".join(
        f"{i+1}. {path}" for i, path in enumerate(preview)
    )


def explain_project_flow():
    return (
        "This project works like this: input comes in through Flask routes, then Jarvis interprets the command "
        "with the router service, sends the result to the dispatcher, and the dispatcher calls the correct service "
        "or handler such as tasks, memory, reminders, developer tools, or system actions."
    )


def suggest_file_improvements(file_path):
    content, error = _read_file(file_path)
    if error:
        return error

    suggestions = []
    lower_name = file_path.lower()

    if "print(" in content:
        suggestions.append("Consider replacing print statements with structured logging.")

    if "except Exception" in content:
        suggestions.append("You may want more specific exception handling instead of catching every exception.")

    if "open(" in content and "encoding=" not in content:
        suggestions.append("Consider always opening text files with an explicit encoding.")

    if "json.dump(" in content and "indent=" not in content:
        suggestions.append("You could add indentation to JSON output to make stored files easier to read.")

    if "def " in content and content.count("def ") > 12:
        suggestions.append("This file may be getting too large and could be split into smaller modules.")

    if lower_name.endswith("app.py"):
        suggestions.append("Keep app.py small so it only sets up Flask and registers routes.")

    if "router_service" in lower_name:
        suggestions.append("The router file may benefit from splitting local rules into helper functions for readability.")

    if "dispatcher" in lower_name:
        suggestions.append("The dispatcher may be easier to maintain if actions are grouped by domain, like tasks, memory, and developer tools.")

    if "Blueprint(" in content:
        suggestions.append("Route files should stay focused on request handling and avoid mixing in too much business logic.")

    if not suggestions:
        return f"I did not find any obvious improvement suggestions for {file_path}, but the file looks reasonably structured."

    return f"Here are some suggestions for {file_path}: " + " ".join(
        f"{i+1}. {s}" for i, s in enumerate(suggestions)
    )


def review_file(file_path):
    analysis = analyze_file(file_path)
    suggestions = suggest_file_improvements(file_path)

    return analysis + "\n\n" + suggestions


def detect_project_issues():
    collected = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "venv"}]

        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                collected.append(rel_path)

    if not collected:
        return "I could not find any Python files to inspect."

    issues = []

    for path in collected:
        content, error = _read_file(path)
        if error or not content:
            continue

        if content.count("print(") >= 3:
            issues.append(f"{path} uses many print statements and may need proper logging.")

        if content.count("except Exception") >= 1:
            issues.append(f"{path} uses broad exception handling, which can hide more specific errors.")

        if content.count("def ") > 15:
            issues.append(f"{path} is getting large and may need to be split into smaller modules.")

        if "client.responses.create" in content:
            issues.append(f"{path} depends on the OpenAI API, so it may need stronger fallback handling and cost control.")

        if "Blueprint(" in content and content.count("def ") > 4:
            issues.append(f"{path} may be mixing route logic with too much processing logic.")

    if not issues:
        return "I did not find any obvious structural issues in the backend."

    return "Here are some likely weak points in the backend: " + " ".join(
        f"{i+1}. {issue}" for i, issue in enumerate(issues[:10])
    )


def suggest_next_refactor():
    return (
        "The next refactor should probably focus on keeping responsibilities separate. "
        "The highest-value areas are usually the router service if it keeps growing, "
        "the dispatcher if many domains are mixed together, and any service file that is becoming too large."
    )


def get_refactor_targets():
    targets = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "venv"}]

        for file in files:
            if file.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                content, error = _read_file(rel_path)
                if error or not content:
                    continue

                score = 0
                if content.count("def ") > 10:
                    score += 2
                if content.count("print(") > 2:
                    score += 1
                if content.count("except Exception") > 0:
                    score += 1
                if "if " in content and rel_path.endswith("router_service.py"):
                    score += 2

                if score > 0:
                    targets.append((score, rel_path))

    if not targets:
        return "I did not find any strong refactor targets yet."

    targets.sort(reverse=True)
    preview = [path for _, path in targets[:5]]

    return "The best refactor targets appear to be: " + " ".join(
        f"{i+1}. {path}" for i, path in enumerate(preview)
    )


def open_project_in_vscode():
    try:
        subprocess.Popen(["open", "-a", "Visual Studio Code", "."])
        return "Opening the current project in Visual Studio Code."
    except Exception as e:
        return f"I could not open the project in VS Code: {str(e)}"


def open_file_in_vscode(file_path):
    if not os.path.exists(file_path):
        return f"I could not find the file {file_path}."

    try:
        subprocess.Popen(["open", "-a", "Visual Studio Code", file_path])
        return f"Opening {file_path} in Visual Studio Code."
    except Exception as e:
        return f"I could not open {file_path} in VS Code: {str(e)}"


def generate_fix_checklist(error_text):
    text = (error_text or "").strip()

    if not text:
        return "Please give me an error message first."

    lowered = text.lower()

    if "connection refused" in lowered:
        return (
            "Fix checklist: "
            "1. Make sure the backend server is running. "
            "2. Confirm the server is listening on the expected port. "
            "3. Check that the request URL matches the backend port and route. "
            "4. Restart the backend and test again."
        )

    if "no module named" in lowered or "modulenotfounderror" in lowered:
        return (
            "Fix checklist: "
            "1. Install the missing package. "
            "2. Verify the selected Python interpreter. "
            "3. Check that the import name matches the installed package. "
            "4. Restart the app after installation."
        )

    if "importerror" in lowered:
        return (
            "Fix checklist: "
            "1. Check the file and function names being imported. "
            "2. Make sure __init__.py files exist where needed. "
            "3. Confirm you are running from the correct project folder. "
            "4. Restart the backend after changing imports."
        )

    if "500" in lowered or "internal server error" in lowered:
        return (
            "Fix checklist: "
            "1. Read the backend traceback carefully. "
            "2. Identify the exact line that failed. "
            "3. Check request input values. "
            "4. Add logging around the failing section and retry."
        )

    return (
        f"Fix checklist for '{text}': "
        "1. Read the full error message carefully. "
        "2. Identify the file and line involved. "
        "3. Check imports, paths, and input data. "
        "4. Re-run the command after one change at a time."
    )

def diagnose_error(error_text):
    text = (error_text or "").strip()

    if not text:
        return "Please give me an error message first."

    lowered = text.lower()

    if "connection refused" in lowered:
        return (
            "Diagnosis: the client is trying to connect to a backend service that is not currently running, "
            "not listening on the expected port, or using the wrong URL."
        )

    if "modulenotfounderror" in lowered or "no module named" in lowered:
        return (
            "Diagnosis: Python cannot find the requested package or module. "
            "This is usually caused by a missing installation, wrong interpreter, or incorrect import path."
        )

    if "importerror" in lowered:
        return (
            "Diagnosis: Python found the package, but could not import the requested name. "
            "This often means the function name, file name, package structure, or __init__.py setup is wrong."
        )

    if "500" in lowered or "internal server error" in lowered:
        return (
            "Diagnosis: the backend crashed while handling the request. "
            "The real cause should appear in the Flask traceback or server logs."
        )

    return f"Diagnosis: I do not have a special rule for '{text}', but it likely needs a traceback, file location, and context to debug properly."

def suggest_root_cause(error_text):
    text = (error_text or "").strip()
    lowered = text.lower()

    if "connection refused" in lowered:
        return "Likely root cause: the Flask server is not running, crashed, or the client is using the wrong port."

    if "modulenotfounderror" in lowered or "no module named" in lowered:
        return "Likely root cause: the dependency is not installed in the active environment or the wrong Python interpreter is selected."

    if "importerror" in lowered:
        return "Likely root cause: the import target does not exist where Python expects it, or package structure changed."

    if "500" in lowered or "internal server error" in lowered:
        return "Likely root cause: an exception happened inside your backend route or service code."

    return "Likely root cause: you need the full traceback and the exact file or command involved."

def help_fix_error(error_text):
    diagnosis = diagnose_error(error_text)
    root_cause = suggest_root_cause(error_text)
    checklist = generate_fix_checklist(error_text)

    return diagnosis + " " + root_cause + " " + checklist