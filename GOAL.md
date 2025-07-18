### **Final Goal Specification for `ppt2video` v2.0.0**

**1. Core Objective**
The script's purpose is to convert a presentation file (`.tex` or `.pdf`) and a corresponding narration script file into a synchronized, narrated video.

**2. Core Features**
*   **Dual-Format Presentation Input**: Accepts either a LaTeX source file (`.tex`) or a ready-to-use PDF file (`.pdf`) as the visual input via the `--presentation` argument.
*   **Automatic Processing**: 
    *   If a `.tex` file is provided, it is first compiled into a PDF.
    *   The final PDF (either provided directly or compiled) is then converted page-by-page into slides for the video.
*   **Synchronized Narration**: Reads a corresponding script file (`--script`) and uses the system's TTS engine to generate narration for each slide, synchronized by page number.
*   **High-Quality Visuals**: Leverages LaTeX (either directly or via a pre-compiled PDF) for professional typesetting and visual presentation.
*   **Silent Slides**: PDF pages that do not have a corresponding narration block in the script file are treated as silent slides with a configurable duration.

**3. Customization Options**
The script is configurable via a rich set of command-line options:
*   `--presentation <file>`: **Required**. Path to the presentation file (either `.tex` or `.pdf`).
*   `--script <file>`: **Required**. Path to the narration script Markdown file.
*   `--output <file>`: Output video file name. (Default: `output.mp4`)
*   `--resolution <WxH>`: Video resolution. (Default: `1920x1080`)
*   `--voice <name>`: Specify the TTS voice to use (e.g., `Tingting`).
*   `--silent-duration <sec>`: Duration for silent slides. (Default: `3`)
*   `--narration-delay <sec>`: Delay in seconds before narration starts on each slide. (Default: `0.0`)
*   `--list-voices`: List all available TTS voices on the system and exit.
*   `--help`: Display the help message.

**4. Robustness & Dependencies**
*   **macOS Focused**: Relies on the `say` command for TTS, making it primarily for macOS.
*   **Dependency-Aware**: 
    *   **`ffmpeg`** is required for all media operations.
    *   A **LaTeX distribution** (e.g., MacTeX, TeX Live) providing `xelatex` is **only required if the presentation input is a `.tex` file**.
    *   The script will exit gracefully if required dependencies are not found.
*   **Voice Validation**: The script checks if the specified voice is available on the system and will exit with an error if it is not, preventing silent fallbacks.