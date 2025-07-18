#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import tempfile
import shutil
import atexit
import subprocess
import os
import re

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert a presentation file (.tex or .pdf) and a script file into a narrated video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--presentation", required=True, help="Path to the presentation file (either .tex or .pdf).")
    parser.add_argument("--script", required=True, help="Path to the narration script Markdown file.")
    parser.add_argument("--output", default="output.mp4", help="Output video file name.")
    parser.add_argument("--resolution", default="1920x1080", help="Video resolution in WxH format.")
    parser.add_argument("--voice", default="Tingting", help="TTS voice to use (macOS only).")
    parser.add_argument("--list-voices", action="store_true", help="List available TTS voices and exit.")
    parser.add_argument("--silent-duration", type=int, default=3, help="Duration for silent slides in seconds.")
    parser.add_argument("--chars-per-second", type=int, default=20, help="Characters per second for reading time calculation.")
    parser.add_argument("--narration-delay", type=float, default=0.0, help="Delay in seconds before narration starts on each slide.")
    return parser.parse_args()

def check_dependencies(is_tex: bool):
    """Checks for required command-line tool dependencies."""
    if is_tex and not shutil.which("xelatex"):
        print("Error: xelatex command not found. Is a LaTeX distribution (like MacTeX) installed?")
        sys.exit(1)
    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg command not found. Please install it.")
        sys.exit(1)
    if not shutil.which("pdfinfo"):
        print("Error: pdfinfo command not found. Is poppler installed? (e.g., 'brew install poppler')")
        sys.exit(1)
    if not shutil.which("pdftoppm"):
        print("Error: pdftoppm command not found. Is poppler installed? (e.g., 'brew install poppler')")
        sys.exit(1)
    if not shutil.which("pdftotext"):
        print("Error: pdftotext command not found. Is poppler installed? (e.g., 'brew install poppler')")
        sys.exit(1)
    if sys.platform == "darwin" and not shutil.which("say"):
        print("Error: 'say' command not found. This script currently relies on macOS for TTS.")
        sys.exit(1)

def get_available_voices() -> list[str]:
    """Returns a list of available voices from the 'say' command."""
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=True)
        return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

def compile_latex_to_pdf(tex_file: str, temp_dir: str) -> str:
    """Compiles a .tex file into a .pdf using xelatex."""
    print(f"   - Compiling {os.path.basename(tex_file)} to PDF using xelatex...")
    pdf_path = os.path.join(temp_dir, os.path.basename(tex_file).replace(".tex", ".pdf"))
    command = [
        "xelatex",
        "-interaction=nonstopmode",
        "-output-directory", temp_dir,
        tex_file
    ]
    try:
        # Run twice to ensure all cross-references are resolved
        subprocess.run(command, check=True, capture_output=True, text=True)
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"     - PDF generated: {pdf_path}")
        return pdf_path
    except subprocess.CalledProcessError as e:
        print("Error during LaTeX compilation.")
        # Attempt to read the log file for more details
        log_file = os.path.join(temp_dir, os.path.basename(tex_file).replace(".tex", ".log"))
        if os.path.exists(log_file):
            print(f"--- LaTeX Log File ({log_file}) ---")
            with open(log_file, 'r') as f:
                print(f.read())
            print("--- End Log File ---")
        else:
            print(f"stdout:\n{e.stdout}")
            print(f"stderr:\n{e.stderr}")
        sys.exit(1)

def get_pdf_dimensions(pdf_path: str) -> tuple[int, int]:
    """Gets the dimensions (width, height) of the first page of a PDF using pdfinfo."""
    try:
        command = ["pdfinfo", pdf_path]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        width, height = 0, 0
        for line in result.stdout.splitlines():
            if line.lower().startswith("page size:"):
                # Example: Page size: 595 x 842 pts (A4)
                parts = line.split()
                width = float(parts[2])
                height = float(parts[4])
                break
        if width == 0 or height == 0:
            raise ValueError("Could not find page size in pdfinfo output.")
        return int(width), int(height)
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting PDF dimensions: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def get_pdf_page_count(pdf_path: str) -> int:
    """Gets the number of pages in a PDF file using pdfinfo."""
    try:
        command = ["pdfinfo", pdf_path]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.lower().startswith("pages:"):
                return int(line.split(':')[1].strip())
        raise ValueError("Could not find page count in pdfinfo output.")
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting PDF page count: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def extract_pdf_pages_as_images(pdf_path: str, page_count: int, resolution: str, temp_dir: str) -> list[str]:
    """Extracts each page of a PDF into a PNG image file using pdftoppm, preserving aspect ratio."""
    print("   - Extracting PDF pages as images using pdftoppm...")
    target_width, target_height = map(int, resolution.split('x'))

    # Get original PDF dimensions to calculate aspect ratio
    pdf_width, pdf_height = get_pdf_dimensions(pdf_path)
    pdf_aspect_ratio = pdf_width / pdf_height

    # Calculate scaling to fit within target resolution while preserving aspect ratio
    # Scale by width
    scale_width = target_width
    scale_height = int(target_width / pdf_aspect_ratio)

    if scale_height > target_height:
        # If scaling by width makes height too large, scale by height instead
        scale_height = target_height
        scale_width = int(target_height * pdf_aspect_ratio)

    output_prefix = os.path.join(temp_dir, "slide")
    command = [
        "pdftoppm",
        "-png",
        "-r", "300", # Set DPI to 300 for higher quality output
        "-scale-to-x", str(scale_width),
        "-scale-to-y", str(scale_height),
        pdf_path,
        output_prefix
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        # Find generated images, sort them, and verify the count.
        generated_files = sorted([
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir)
            if f.startswith("slide-") and f.endswith(".png")
        ])
        if len(generated_files) != page_count:
            raise RuntimeError(
                f"pdftoppm generated {len(generated_files)} images, but {page_count} were expected."
            )
        for path in generated_files:
            print(f"     - Image found: {path}")
        return generated_files
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError) as e:
        print(f"Error during PDF page extraction (pdftoppm): {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)


def get_text_from_pdf_page(pdf_path: str, page_num: int) -> str:
    """Extracts text from a specific page of a PDF using pdftotext."""
    try:
        # pdftotext uses 1-based indexing for pages
        command = ["pdftotext", "-f", str(page_num), "-l", str(page_num), pdf_path, "-"]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error extracting text from PDF page {page_num}: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def calculate_reading_time(text: str, chars_per_second: int) -> float:
    """Calculates reading time based on character count and reading speed."""
    if not text or chars_per_second <= 0:
        return 0.0
    # Count Chinese characters as 2, English characters as 1
    char_count = 0
    for char in text:
        if '\u4e00' <= char <= '\u9fff':  # Check if it's a Chinese character
            char_count += 2
        else:
            char_count += 1
    return char_count / chars_per_second

def preprocess_text_for_tts(text: str) -> str:
    """Preprocesses text to improve TTS pronunciation and remove metadata."""
    # Remove [cite_start] and [cite n] markers
    text = re.sub(r'\[cite[^\]]*\]', '', text)
    # Remove Markdown bolding (**) and italics (*)
    text = re.sub(r'\*\*|\*', '', text)
    # Remove list markers (*, -, +) at the beginning of lines
    text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    # Replace AI with A. I.
    text = re.sub(r'\bAI\b', 'A. I.', text, flags=re.IGNORECASE)
    return text.strip()

def generate_audio_file(text: str, voice: str, output_path: str, temp_dir: str) -> str:
    """Generates an AIFF audio file from text using the 'say' command."""
    try:
        processed_text = preprocess_text_for_tts(text)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix=".txt") as temp_text_file:
            temp_text_file.write(processed_text)
            temp_text_path = temp_text_file.name
        command = ["say", "-v", voice, "-o", output_path, "--file-format=AIFF", "-f", temp_text_path]
        subprocess.run(command, check=True, capture_output=True, text=True)
        os.remove(temp_text_path)
        return output_path
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error during audio generation: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def get_audio_duration(file_path: str) -> float:
    """Gets the duration of an audio file in seconds using ffprobe."""
    try:
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting audio duration: {e}")
        sys.exit(1)

def generate_video_segment(image_path: str, audio_path: str, duration: float, output_path: str, resolution: str, narration_delay: float) -> str:
    """Generates a single video segment for a slide from its image and audio."""
    try:
        width, height = resolution.split('x')
        command = ["ffmpeg", "-y", "-loop", "1", "-i", image_path]
        
        # Create a silent audio track for the delay
        silent_audio_input = f"anullsrc=channel_layout=stereo:sample_rate=44100:d={narration_delay}"

        if audio_path:
            # Concatenate silent audio with narration audio
            command.extend(["-i", audio_path])
            audio_filter = f"{silent_audio_input}[silent];[silent][1:a]concat=n=2:v=0:a=1[aout]"
            command.extend(["-filter_complex", audio_filter, "-map", "[aout]", "-map", "0:v"])
        else: # Silent slide, just use the delay as the audio
            command.extend(["-f", "lavfi", "-i", silent_audio_input])

        command.extend([
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-t", str(duration), 
            "-s", resolution, "-shortest", output_path
        ])
        
        subprocess.run(command, check=True, capture_output=True, text=True)
        return output_path
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error during video segment generation: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def concatenate_videos(segment_paths: list[str], output_path: str, temp_dir: str):
    """Concatenates multiple video segments into a single video file."""
    try:
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, 'w') as f:
            for path in segment_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        command = [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_path,
            "-c", "copy", "-y", output_path
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"\nFinal video successfully generated at: {output_path}")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error during video concatenation: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def parse_script_file(script_file: str, page_count: int) -> dict[int, str]:
    """
    Parses the narration script file, extracting narration for each slide.
    Narration for a slide starts after '(幻灯片 n: ...)' and ends before the next '---' or the next '(幻灯片 n+1: ...)' marker.
    """
    narrations = {}
    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all slide markers and their positions
        # Store (slide_num, start_of_marker_pos, end_of_marker_pos)
        slide_marker_info = []
        for match in re.finditer(r'\*\*\(幻灯片\s*(\d+):[^\)]*\)\*\*|\(幻灯片\s*(\d+):[^\)]*\)', content, re.DOTALL):
            # Determine which group matched (bolded or non-bolded)
            slide_num = int(match.group(1) or match.group(2))
            slide_marker_info.append((slide_num, match.start(), match.end()))
        
        # Sort by slide number (should already be sorted by finditer, but good practice)
        slide_marker_info.sort()

        # Extract narration for each slide
        for i, (current_slide_num, current_marker_start_pos, current_marker_end_pos) in enumerate(slide_marker_info):
            current_narration_start_pos = current_marker_end_pos
            # Advance past any trailing ** that belong to the marker
            trailing_bold_match = re.match(r'^\s*\*\*', content[current_narration_start_pos:])
            if trailing_bold_match:
                current_narration_start_pos += trailing_bold_match.end()
            narration_end_pos = len(content) # Default to end of file

            # Find the position of the next slide marker (if any)
            next_marker_start_pos = len(content)
            if i + 1 < len(slide_marker_info):
                next_marker_start_pos = slide_marker_info[i+1][1] # Start of the next marker

            # Find the position of the next '---' after the current marker
            # Search only up to the next marker to avoid finding '---' from later sections
            search_limit_for_dash = min(len(content), next_marker_start_pos)
            dash_match = re.search(r'\n---', content[current_narration_start_pos:search_limit_for_dash])
            
            if dash_match:
                next_dash_pos = current_narration_start_pos + dash_match.start()
                # The narration ends at the minimum of the next marker or the next dash
                narration_end_pos = min(next_marker_start_pos, next_dash_pos)
            else:
                # If no '---' found, narration ends at the next marker or end of file
                narration_end_pos = next_marker_start_pos
            
            # Ensure narration_end_pos is not before current_narration_start_pos
            narration_end_pos = max(current_narration_start_pos, narration_end_pos)

            narration_text = content[current_narration_start_pos:narration_end_pos].strip()
            narrations[current_slide_num] = narration_text

        # Ensure all slides have a narration entry, even if empty
        for i in range(1, page_count + 1):
            if i not in narrations:
                narrations[i] = "" # Assign empty string for silent slides if no entry found

    except FileNotFoundError:
        print(f"Error: Script file not found at {script_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing script file: {e}")
        sys.exit(1)
    return narrations

def main():
    """Main function to run the script."""
    args = parse_arguments()
    
    if args.list_voices:
        print("Available TTS voices:")
        voices = get_available_voices()
        if voices:
            for voice in voices:
                print(f"  - {voice}")
        else:
            print("Could not retrieve voices. Is 'say' command available?")
        sys.exit(0)

    is_tex = args.presentation.lower().endswith('.tex')
    check_dependencies(is_tex)
    temp_dir = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, temp_dir)

    print("---------------------------------")
    print("PPT to Video Converter (v2.0.0)")
    print("---------------------------------")
    
    if sys.platform == "darwin":
        available_voices = get_available_voices()
        if available_voices and args.voice not in available_voices:
            print(f"Error: Voice '{args.voice}' not found on this system.")
            print("Use --list-voices to see available options.")
            sys.exit(1)
    
    for key, value in vars(args).items():
        print(f"{key.replace('_', ' ').capitalize():<20}: {value}")
    print(f"{'Temporary dir':<20}: {temp_dir}")
    print("---------------------------------")

    if is_tex:
        print("1. Compiling LaTeX to PDF...")
        pdf_path = compile_latex_to_pdf(args.presentation, temp_dir)
    else:
        print("1. Using existing PDF...")
        pdf_path = args.presentation

    print("\n2. Preparing images from PDF...")
    page_count = get_pdf_page_count(pdf_path)
    image_paths = extract_pdf_pages_as_images(pdf_path, page_count, args.resolution, temp_dir)
    print(f"   - Found {page_count} pages in the PDF.")

    print("\n3. Parsing script and preparing audio...")
    narrations = parse_script_file(args.script, page_count)
    print(f"   - Found {len(narrations)} narration blocks.")

    slide_data_list = []
    for i, image_path in enumerate(image_paths):
        slide_num = i + 1
        data = {"image_path": image_path, "audio_path": None, "duration": args.silent_duration + args.narration_delay}
        narration = narrations.get(slide_num)
        
        if narration:
            print(f"   - Generating audio for Slide {slide_num}...")
            audio_path = os.path.join(temp_dir, f"slide_{slide_num}.aiff")
            generate_audio_file(narration, args.voice, audio_path, temp_dir)
            duration = get_audio_duration(audio_path)
            data["audio_path"] = audio_path
            data["duration"] = duration + args.narration_delay
            print(f"     - Audio generated: {audio_path} (Duration: {duration:.2f}s + {args.narration_delay:.2f}s delay)")
        else:
            print(f"   - Slide {slide_num} is silent (Duration: {args.silent_duration}s + {args.narration_delay:.2f}s delay).")
            
        slide_data_list.append(data)

    print("\n4. Generating video segments...")
    segment_paths = []
    for i, slide_data in enumerate(slide_data_list):
        print(f"   - Generating segment for Slide {i+1}...")
        segment_path = os.path.join(temp_dir, f"segment_{i+1}.mp4")
        generate_video_segment(slide_data["image_path"], slide_data["audio_path"], slide_data["duration"], segment_path, args.resolution, args.narration_delay)
        segment_paths.append(segment_path)
        print(f"     - Segment generated: {segment_path}")

    print("\n5. Assembling final video...")
    concatenate_videos(segment_paths, args.output, temp_dir)

    print("\n---------------------------------")
    print("Processing complete.")

if __name__ == "__main__":
    main()