### **Final Goal Specification for `ppt2video` v1.0.0**

**1. Core Objective**
The script's purpose is to convert a Markdown presentation file and a corresponding narration script file into a synchronized, narrated video.

**2. Core Features**
*   **Markdown-to-Video**: Converts a Markdown file (`--presentation`) containing slides separated by `---` into a video.
*   **Synchronized Narration**: Reads a corresponding script file (`--script`) and uses the system's TTS engine to generate narration for each slide.
*   **Dynamic Font Sizing**: Automatically calculates the optimal font size for each slide to ensure all text fits within the screen boundaries without manual wrapping. The original line breaks from the Markdown file are preserved.
*   **Silent Slides**: Slides present in the presentation file but absent from the script file are treated as silent slides with a configurable duration.

**3. Customization Options**
The script is configurable via a rich set of command-line options:
*   `--presentation <file>`: **Required**. Path to the presentation Markdown file.
*   `--script <file>`: **Required**. Path to the narration script Markdown file.
*   `--output <file>`: Output video file name. (Default: `output.mp4`)
*   `--resolution <WxH>`: Video resolution. (Default: `1920x1080`)
*   `--bg-color <color>`: Video background color. (Default: `black`)
*   `--bg-image <path>`: Use an image for the background.
*   `--voice <name>`: Specify the TTS voice to use (e.g., `Tingting`).
*   `--font-file <path>`: Path to a `.ttf` or `.ttc` font file.
*   `--font-size <num>`: **Maximum** font size to use for dynamic scaling. (Default: `120`)
*   `--margin <num>`: Margin around the text block. (Default: `100`)
*   `--silent-duration <sec>`: Duration for silent slides. (Default: `3`)
*   `--list-voices`: List all available TTS voices on the system and exit.
*   `--help`: Display the help message.

**4. Robustness & Dependencies**
*   **macOS Focused**: Relies on the `say` command for TTS, making it primarily for macOS.
*   **Dependency-Aware**: The script requires `ffmpeg` for all media operations and the Python `Pillow` library for font size calculations. It will exit gracefully if dependencies are not found.
*   **Voice Validation**: The script checks if the specified voice is available on the system and will exit with an error if it is not, preventing silent fallbacks.
