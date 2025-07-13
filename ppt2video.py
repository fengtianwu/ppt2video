#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import tempfile
import shutil
import atexit
import subprocess

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert a presentation Markdown file and a script file into a narrated video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--presentation",
        required=True,
        help="Path to the presentation Markdown file."
    )
    parser.add_argument(
        "--script",
        required=True,
        help="Path to the narration script Markdown file."
    )
    parser.add_argument(
        "--output",
        default="output.mp4",
        help="Output video file name."
    )
    parser.add_argument(
        "--resolution",
        default="1920x1080",
        help="Video resolution in WxH format."
    )
    parser.add_argument(
        "--bg-color",
        default="black",
        help="Video background color."
    )
    parser.add_argument(
        "--bg-image",
        default=None,
        help="Path to a background image (overrides bg-color)."
    )
    parser.add_argument(
        "--voice",
        default="Ting-Ting",
        help="TTS voice to use (macOS only)."
    )
    parser.add_argument(
        "--font-file",
        default="/System/Library/Fonts/PingFang.ttc",
        help="Path to a .ttf or .ttc font file."
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=48,
        help="Font size for the text."
    )
    parser.add_argument(
        "--silent-duration",
        type=int,
        default=3,
        help="Duration for silent slides in seconds."
    )

    return parser.parse_args()

def parse_presentation_file(filename: str) -> list[str]:
    """
    Parses the presentation file, splitting it into slides.
    Each slide is a string.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        # Split by '---' and filter out any empty strings from leading/trailing separators
        slides = [slide.strip() for slide in content.split('\n---\n') if slide.strip()]
        return slides
    except FileNotFoundError:
        print(f"Error: Presentation file not found at '{filename}'")
        sys.exit(1)

def parse_script_file(filename: str) -> dict[str, str]:
    """
    Parses the script file into a dictionary mapping slide titles to narrations.
    """
    narrations = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        blocks = [block.strip() for block in content.split('\n---\n') if block.strip()]
        
        # Skip the first block if it's a general header
        if blocks and not blocks[0].startswith("###"):
            blocks = blocks[1:]

        for block in blocks:
            lines = block.split('\n')
            # The title is the first line. Remove '###' and any markdown formatting like '**'
            title = lines[0].replace('###', '').replace('**', '').strip()
            # The rest of the lines are the narration
            narration = '\n'.join(lines[1:]).strip()
            if title:
                narrations[title] = narration
        return narrations
    except FileNotFoundError:
        print(f"Error: Script file not found at '{filename}'")
        sys.exit(1)

def generate_audio_file(text: str, voice: str, output_path: str, temp_dir: str) -> str:
    """
    Generates an AIFF audio file from text using the 'say' command.
    It writes the text to a temporary file to avoid command line length limits.
    Returns the path to the generated file.
    """
    try:
        # Create a temporary file to hold the narration text
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix=".txt") as temp_text_file:
            temp_text_file.write(text)
            temp_text_path = temp_text_file.name

        # Use the 'say' command with the -f flag to read from the file
        command = [
            "say",
            "-v", voice,
            "-o", output_path,
            "--file-format=AIFF",
            "-f", temp_text_path
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        
        # Clean up the temporary text file
        os.remove(temp_text_path)
        
        return output_path
    except FileNotFoundError:
        print("Error: 'say' command not found. This script currently requires macOS for TTS.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'say' command: {e}")
        print(f"Stderr: {e.stderr}")
        sys.exit(1)

def get_audio_duration(file_path: str) -> float:
    """
    Gets the duration of an audio file in seconds using ffprobe.
    """
    try:
        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except FileNotFoundError:
        print("Error: 'ffprobe' command not found. This script requires ffmpeg to be installed.")
        sys.exit(1)
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting duration for {file_path} using ffprobe: {e}")
        if 'result' in locals():
            print(f"Stdout from ffprobe: {result.stdout}")
            print(f"Stderr from ffprobe: {result.stderr}")
        sys.exit(1)

import os

def generate_image_for_slide(slide_content: str, args: argparse.Namespace, output_path: str, temp_dir: str):
    """
    Generates a PNG image for a single slide using ffmpeg.
    """
    try:
        # Write the slide content to a temporary text file for ffmpeg's drawtext filter
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix=".txt") as temp_text_file:
            # Clean up the slide content for display - remove the title line itself
            display_text = '\n'.join(slide_content.split('\n')[1:]).strip()
            temp_text_file.write(display_text)
            text_file_path = temp_text_file.name

        # Base ffmpeg command
        command = ["ffmpeg"]

        # Set up the input - either a background image or a generated color
        if args.bg_image:
            command.extend(["-i", args.bg_image])
        else:
            command.extend(["-f", "lavfi", "-i", f"color=c={args.bg_color}:s={args.resolution}"])
        
        # Add the drawtext filter
        margin = 100 # Simple margin for now
        command.extend([
            "-vf", f"drawtext=fontfile='{args.font_file}':textfile='{text_file_path}':"
                   f"fontcolor=white:fontsize={args.font_size}:"
                   f"x={margin}:y={margin}",
            "-frames:v", "1", # We only need a single image frame
            "-y", # Overwrite output file if it exists
            output_path
        ])

        subprocess.run(command, check=True, capture_output=True, text=True)
        os.remove(text_file_path)

    except FileNotFoundError:
        print("Error: 'ffmpeg' command not found. This script requires ffmpeg to be installed.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error generating image for slide: {e}")
        print(f"Stderr from ffmpeg: {e.stderr}")
        sys.exit(1)

def generate_video_segment(slide_data: dict, args: argparse.Namespace, output_path: str):
    """
    Generates a single video segment for a slide from its image and audio.
    """
    try:
        command = ["ffmpeg"]
        
        # Input image
        command.extend(["-loop", "1", "-i", slide_data["image_path"]])
        
        # Input audio
        if slide_data["audio_path"]:
            command.extend(["-i", slide_data["audio_path"]])
        else:
            # For silent slides, generate a silent audio stream
            command.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

        command.extend([
            "-c:v", "libx264",       # Video codec
            "-c:a", "aac",           # Audio codec
            "-b:a", "192k",          # Audio bitrate
            "-pix_fmt", "yuv420p",   # Pixel format for compatibility
            "-t", str(slide_data["duration"]), # Set the duration of the segment
            "-shortest",             # Finish encoding when the shortest input stream ends
            "-y",
            output_path
        ])
        
        subprocess.run(command, check=True, capture_output=True, text=True)

    except FileNotFoundError:
        print("Error: 'ffmpeg' command not found. This script requires ffmpeg to be installed.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error generating video segment for slide '{slide_data['title']}': {e}")
        print(f"Stderr from ffmpeg: {e.stderr}")
        sys.exit(1)

def concatenate_videos(segment_paths: list[str], output_path: str, temp_dir: str):
    """
    Concatenates multiple video segments into a single video file using ffmpeg.
    """
    try:
        # Create a text file listing all the segments to be concatenated
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, 'w') as f:
            for path in segment_paths:
                # The format for the concat demuxer is "file '/path/to/file.mp4'"
                f.write(f"file '{os.path.abspath(path)}'\n")

        command = [
            "ffmpeg",
            "-f", "concat",          # Use the concat demuxer
            "-safe", "0",            # Needed for absolute paths in the list file
            "-i", concat_list_path,  # The list of files to concatenate
            "-c", "copy",            # Copy streams without re-encoding
            "-y",
            output_path
        ]
        
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"\nFinal video successfully generated at: {output_path}")

    except FileNotFoundError:
        print("Error: 'ffmpeg' command not found. This script requires ffmpeg to be installed.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error concatenating video segments: {e}")
        print(f"Stderr from ffmpeg: {e.stderr}")
        sys.exit(1)

def main():
    """Main function to run the script."""
    args = parse_arguments()

    # Create a temporary directory for intermediate files
    temp_dir = tempfile.mkdtemp()
    # Register a cleanup function to remove the directory on exit
    # atexit.register(shutil.rmtree, temp_dir) # Temporarily disable for debugging if needed

    print("---------------------------------")
    print("PPT to Video Converter (Python)")
    print("---------------------------------")
    for key, value in vars(args).items():
        print(f"{key.replace('_', ' ').capitalize():<20}: {value}")
    print(f"{'Temporary dir':<20}: {temp_dir}")
    print("---------------------------------")

    print("1. Parsing files...")
    slides = parse_presentation_file(args.presentation)
    narrations = parse_script_file(args.script)
    print(f"   - Found {len(slides)} slides.")
    print(f"   - Found {len(narrations)} narration blocks.")

    print("\n2. Processing slides (audio and image generation)...")
    slide_data_list = [] # List to hold dictionaries of slide info
    for i, slide_content in enumerate(slides):
        slide_title = ""
        for line in slide_content.split('\n'):
            if line.startswith('## '):
                slide_title = line.replace('## ', '').strip()
                break
        
        print(f"   - Processing Slide {i+1} ('{slide_title}')...")
        data = {"title": slide_title, "content": slide_content, "audio_path": None, "duration": args.silent_duration, "image_path": None}
        
        # Generate audio and get duration
        narration = narrations.get(slide_title)
        if narration:
            audio_path = f"{temp_dir}/slide_{i+1}.aiff"
            generate_audio_file(narration, args.voice, audio_path, temp_dir)
            duration = get_audio_duration(audio_path)
            data["audio_path"] = audio_path
            data["duration"] = duration
            print(f"     - Audio generated: {audio_path} ({duration:.2f}s)")
        else:
            print(f"     - Silent slide. Duration: {args.silent_duration}s")
        
        # Generate image
        image_path = f"{temp_dir}/slide_{i+1}.png"
        generate_image_for_slide(slide_content, args, image_path, temp_dir)
        data["image_path"] = image_path
        print(f"     - Image generated: {image_path}")

        slide_data_list.append(data)
    
    print("\n3. Generating video segments...")
    segment_paths = []
    for i, slide_data in enumerate(slide_data_list):
        print(f"   - Generating segment for Slide {i+1} ('{slide_data['title']}')...")
        segment_path = f"{temp_dir}/segment_{i+1}.mp4"
        generate_video_segment(slide_data, args, segment_path)
        segment_paths.append(segment_path)
        print(f"     - Segment generated: {segment_path}")

    print("\n4. Assembling final video...")
    concatenate_videos(segment_paths, args.output, temp_dir)

    print("\n---------------------------------")
    print("Processing complete.")
    # Clean up temp dir manually if atexit is disabled
    # shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
