# ppt2video

A Python script to convert a Markdown presentation and a corresponding narration script into a narrated video file.

This tool takes a Markdown file for slide content and a separate Markdown file for the speaker notes, and it generates a video where the slide text is displayed on screen, synchronized with a text-to-speech narration of the speaker notes.

The script's key feature is its **dynamic font sizing**. It automatically calculates the optimal font size for each slide individually to ensure all text fits perfectly on the screen without overflowing, all while preserving the original line breaks from your Markdown file.

## Features

-   Converts Markdown slides (separated by `---`) into video segments.
-   Synchronizes each slide with a corresponding narration script.
-   Uses macOS's built-in `say` command for text-to-speech.
-   **Automatically scales font size** to make text fit the screen.
-   Preserves original line breaks.
-   Supports silent slides.
-   Customizable resolution, background, fonts, and voice.
-   Validates that the specified TTS voice is available on the system.

## Dependencies

-   **Python 3**
-   **ffmpeg**: Must be installed and available in your system's `PATH`.
-   **Pillow**: The Python imaging library. Install it via pip:
    ```bash
    pip install Pillow
    ```

## Usage

The script is run from the command line.

### **Basic Example:**

```bash
python3 ppt2video.py --presentation maga_presentation.md --script maga_presentation_script.md
```

This will generate an `output.mp4` file in the current directory.

### **Command-Line Options**

| Option                | Description                                                 | Default                                       |
| --------------------- | ----------------------------------------------------------- | --------------------------------------------- |
| `--presentation <file>` | **Required**. Path to the presentation Markdown file.       | -                                             |
| `--script <file>`     | **Required**. Path to the narration script Markdown file.   | -                                             |
| `--output <file>`     | Output video file name.                                     | `output.mp4`                                  |
| `--resolution <WxH>`  | Video resolution.                                           | `1920x1080`                                   |
| `--bg-color <color>`  | Video background color (e.g., `black`, `blue`).             | `black`                                       |
| `--bg-image <path>`   | Path to a background image (overrides bg-color).            | -                                             |
| `--voice <name>`      | TTS voice to use.                                           | `Tingting`                                    |
| `--font-file <path>`  | Path to a `.ttf` or `.ttc` font file.                       | `/System/Library/Fonts/Hiragino Sans GB.ttc`  |
| `--font-size <num>`   | **Maximum** font size for dynamic scaling.                  | `120`                                         |
| `--margin <num>`      | Margin around the text block in pixels.                     | `100`                                         |
| `--silent-duration <sec>` | Duration for silent slides in seconds.    | `3`                                           |
| `--narration-delay <sec>` | Delay in seconds before narration starts on each slide. | `0.0`                                         |
| `--list-voices`       | List all available TTS voices on the system and exit.       | -                                             |
| `--help`              | Display the help message.                                   | -                                             |

### **Listing Available Voices**

To see which voices you can use with the `--voice` option, run:

```bash
python3 ppt2video.py --list-voices
```
