import argparse, glob, os, tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from ffmpeg import extract_video, combine_images
from PIL import Image
from tqdm import tqdm


# Global variables for worker processes to avoid repeated pickling
worker_black_img = None
worker_white_img = None


def init_worker(black_img: Image.Image, white_img: Image.Image):
    """Initializes worker processes with the overlay images."""
    global worker_black_img, worker_white_img
    worker_black_img = black_img
    worker_white_img = white_img


def process_single_frame(frame_path: str):
    """Processes a single frame using images from the global worker scope."""
    mask = Image.open(frame_path).convert('L')
    composite_img = Image.composite(worker_white_img, worker_black_img, mask)
    composite_img.save(frame_path)


def process_frames(frames_folder: str, black_image_path: str, white_image_path: str):
    """
    Replaces black and white pixels in frames with corresponding images.

    Args:
        frames_folder (str): Folder containing the grayscale frames.
        black_image_path (str): Path to the image for black areas.
        white_image_path (str): Path to the image for white areas.
    """
    black_img = Image.open(black_image_path).convert("RGB")
    white_img = Image.open(white_image_path).convert("RGB")

    frame_files = sorted(glob.glob(os.path.join(frames_folder, 'frame_*.png')))
    if not frame_files:
        print("No frames found to process.")
        return

    # Get dimensions from the first frame and resize overlay images
    with Image.open(frame_files[0]) as first_frame:
        width, height = first_frame.size
        black_img = black_img.resize((width, height))
        white_img = white_img.resize((width, height))

    print("Processing frames...")
    with ProcessPoolExecutor(initializer=init_worker, initargs=(black_img, white_img)) as executor:
        # Create a list of futures
        futures = [executor.submit(process_single_frame, frame_path) for frame_path in frame_files]
        # Use tqdm to show progress as tasks complete
        for future in tqdm(as_completed(futures), total=len(futures)):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing a frame: {e}")


def main():
    parser = argparse.ArgumentParser(description="Process a video by replacing black and white areas with images.")
    parser.add_argument('--input_video', required=True, help="Path to the input video file.")
    parser.add_argument('--output_video', required=True, help="Path for the final output video.")
    parser.add_argument('--black_image', help="Path to the image for black parts. Defaults to a black image.")
    parser.add_argument('--white_image', help="Path to the image for white parts. Defaults to a white image.")
    parser.add_argument('--fps', type=int, default=0, help="Frames per second for the video. Default is auto-detected.")
    
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")

        black_image_path = args.black_image
        white_image_path = args.white_image

        if not black_image_path:
            black_image_path = os.path.join(temp_dir, 'black.png')
            Image.new('RGB', (1, 1), (0, 0, 0)).save(black_image_path)

        if not white_image_path:
            white_image_path = os.path.join(temp_dir, 'white.png')
            Image.new('RGB', (1, 1), (255, 255, 255)).save(white_image_path)
        
        # 1. Extract frames from the input video
        print("Extracting frames from video...")
        fps = extract_video(args.input_video, temp_dir, args.fps)
        
        # 2. Process each frame
        process_frames(temp_dir, black_image_path, white_image_path)
        
        # 3. Combine processed frames into the output video
        print("Combining frames into output video...")
        combine_images(temp_dir, args.output_video, fps)
        
        print(f"Successfully created video: {args.output_video}")

if __name__ == "__main__":
    main()