import sys
import os

# Ensure project root is on path to import app utils
sys.path.append(os.getcwd())

from app.utils.exif import extract_gps

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_exif.py path/to/image.jpg")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print("File not found:", path)
        sys.exit(1)

    gps = extract_gps(path)
    if gps:
        lat, lng = gps
        print(f"GPS found: {lat}, {lng}")
    else:
        print("No GPS found")

if __name__ == "__main__":
    main()
