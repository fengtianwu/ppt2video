### **Summary of Problems and Lessons Learned**

This document summarizes the key problems encountered during development. Each lesson is assigned an **Error Count**, representing the number of times a category of error caused a failure during our interactive session. Lessons with a higher count were more problematic and should be given special attention in future projects.

---

**1. Problem: Font Rendering, Measurement, and CJK Support (Error Count: 7)**
*   **Issue**: This was the most persistent category of error. Problems included:
    1.  Rendering Chinese characters as "tofu" squares because the default font lacked the necessary glyphs.
    2.  Incorrectly wrapping Chinese text because the logic was word-based (splitting on spaces) instead of character-based.
    3.  Failing to find the correct path to system fonts (`PingFang.ttc`, `STHeitiTC-Medium.ttc`), even with hardcoded paths, due to the complexities of the macOS font system.
*   **Lesson**: Robust multilingual text rendering is extremely difficult.
    1.  **Unify Font Handling**: The exact same font file must be used for both text measurement (`Pillow`) and video rendering (`ffmpeg`).
    2.  **Use CJK-Compatible Fonts**: When CJK text is detected, the script must switch to a known compatible font. The most reliable way to find this font is to use a system utility (e.g., `system_profiler SPFontsDataType`) to get the exact, full path, as simple paths are unreliable.
    3.  **Wrap Character-by-Character**: Logic must iterate character-by-character, not word-by-word, to correctly handle all languages.
    4.  **Provide User Overrides**: Always allow the user to specify their own font file (`--font-file`) as a final fallback.

**2. Problem: Complex Dependencies and Environment Issues (Error Count: 6)**
*   **Issue**: An attempt to render full Markdown formatting using `WeasyPrint` failed due to intractable environment issues. The library could not find its C-language dependencies (`pango`, `libffi`) because of conflicts between the system's Python environment (Anaconda) and Homebrew-installed libraries. Setting environment variables (`DYLD_LIBRARY_PATH`, `LDFLAGS`) was not sufficient to resolve the runtime linking errors.
*   **Lesson**: Avoid complex C-dependencies when a simpler solution exists. The runtime environment is the hardest variable to control. A feature is not worth implementing if it makes the tool brittle and difficult to install. **Prioritize reliability over features.**

**3. Problem: Basic Python Scripting Errors (Error Count: 5)**
*   **Issue**: The development process was plagued by simple `NameError`, `SyntaxError`, and `IndentationError` issues. These were often caused by incorrect refactoring, such as moving the `parser.parse_args()` call to the wrong place or having incorrect indentation in a `try...except` block.
*   **Lesson**: Even with a modular approach, careful attention to basic Python syntax and structure is critical. Frequent, small-scale testing after every change is necessary to catch these simple errors before they compound.

**4. Problem: System Command Integration (`say`) (Error Count: 3)**
*   **Issue**: The macOS `say` command failed in non-obvious ways. It produced a "Bad file descriptor" error when text was piped to it incorrectly, and it failed silently (producing no audio) when a specified voice was not installed or misnamed (`Ting-Ting` vs. `Tingting`).
*   **Lesson**: System commands are external dependencies that can be fragile. It's crucial to add robust error handling that checks for failures and provides users with helpful diagnostic hints (e.g., "Voice not found, run `say -v '?'` to see available voices.").

**5. Problem: Incorrect Business Logic (Markdown Parsing) (Error Count: 1)**
*   **Issue**: The initial implementation of Markdown support stripped all blank lines during the conversion to plain text. This broke the scene-splitting logic, which relies on those blank lines as delimiters.
*   **Lesson**: When transforming data from one format to another, ensure the transformation preserves the essential metadata required by later processing steps. The conversion from Markdown to plain text needed to be more intelligent, preserving paragraph breaks as double newlines for the scene splitter.

**6. Problem: Foundational Design (Shell Scripting) (Error Count: 1)**
*   **Issue**: The very first attempt at this tool was a shell script, which was immediately plagued by subtle syntax errors and an inability to handle floating-point math.
*   **Lesson**: Use the right tool for the job. For tasks involving complex string manipulation, process orchestration, and math, a high-level scripting language like Python is far more robust and appropriate than shell scripting.