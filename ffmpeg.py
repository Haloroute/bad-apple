import os, subprocess

FFMPEG_PATH = os.path.join('ffmpeg', 'bin', 'ffmpeg.exe')
FFPROBE_PATH = os.path.join('ffmpeg', 'bin', 'ffprobe.exe')


def extract_video(input_video: str, output_folder: str, frame_rate: int = 0) -> int:
    """
    Extracts frames from a video file using ffmpeg.

    Args:
        input_video (str): Path to the input video file.
        output_folder (str): Path to the folder where frames will be saved.
        frame_rate (int): The frame rate for extraction. If <= 0, it's auto-detected.
    
    Returns:
        int: The frame rate used for extraction.
    """
    os.makedirs(output_folder, exist_ok=True)

    if frame_rate <= 0:
        try:
            probe_command = [
                FFPROBE_PATH,
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=r_frame_rate',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_video
            ]
            result = subprocess.run(probe_command, capture_output=True, text=True, check=True)
            num, den = map(int, result.stdout.strip().split('/'))
            frame_rate = round(num / den)
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
            print(f"Could not determine FPS automatically, defaulting to 30. Error: {e}")
            frame_rate = 30
    
    command = [
        FFMPEG_PATH,
        '-i', input_video,
        '-r', str(frame_rate),
        '-vf', 'format=gray',
        os.path.join(output_folder, 'frame_%05d.png')
    ]    
    subprocess.run(command, check=True)

    # Extract audio
    audio_command = [
        FFMPEG_PATH,
        '-i', input_video,
        '-vn',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-y',
        os.path.join(output_folder, 'audio.aac')
    ]
    subprocess.run(audio_command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) # check=False in case no audio

    return frame_rate


def combine_images(images_folder: str, output_video: str, frame_rate: int):
    """
    Combines a sequence of images into a video file using ffmpeg.

    Args:
        images_folder (str): Path to the folder containing the image sequence.
        output_video (str): Path to the output video file.
        frame_rate (int): Frame rate for the output video.
    """
    audio_path = os.path.join(images_folder, 'audio.aac')
    has_audio = os.path.exists(audio_path)

    command = [
        FFMPEG_PATH,
        '-r', str(frame_rate),
        '-i', os.path.join(images_folder, 'frame_%05d.png'),
    ]

    if has_audio:
        command.extend(['-i', audio_path, '-c:a', 'aac', '-shortest'])

    command.extend([
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-y',  # Overwrite output file if it exists
        output_video
    ])
    subprocess.run(command, check=True)