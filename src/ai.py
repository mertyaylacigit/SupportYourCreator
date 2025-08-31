import cv2
import pytesseract
import re
import logging
import time
import os
import sys
import numpy as np
import aiohttp
import asyncio
from matplotlib import pyplot as plt
from fuzzywuzzy import process
from config import LOGGING_LEVEL, SECRET_TIMETRACKER_KEY

#pytesseract.pytesseract.tesseract_cmd = "/nix/store/73fd7sj6spffmshv6q5ijjqxf5zmjfbk-tesseract-5.3.0/bin/tesseract"

# ✅ Setup logging configuration
logging.basicConfig(
    level=LOGGING_LEVEL,  # Capture ALL logs (INFO, DEBUG, ERROR)
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs are printed
    ]
)
logger = logging.getLogger(__name__)  # ✅ Use logger instead of print()

# ✅ Define expected OCR keys (lowercase for better matching)
EXPECTED_KEYS = {"name", "hash", "played time (in minutes)"}

# ✅ Set custom tessdata directory (for fast OCR model)
custom_tessdata_dir = "models"
custom_config = f"--tessdata-dir {custom_tessdata_dir} --oem 3 --psm 6"
model = "eng_fast"


async def fetch_image_from_cdn(image_url):
    """
    Fetches an image from a Discord CDN URL and converts it to an OpenCV format.

    :param image_url: The URL of the image to fetch.
    :return: OpenCV image (NumPy array) or None if an error occurs.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    logger.error(f"❌ Failed to fetch image: HTTP {response.status}")
                    return None

                image_bytes = await response.read()

        # ✅ Convert bytes to NumPy array and decode image
        np_arr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image is None:
            logger.error("❌ Invalid image format or decoding failed.")
            return None

        return image

    except Exception as e:
        logger.error(f"❌ Error fetching image: {e}")
        return None

async def check_image(image_url, display=False):
    """
    Processes an image from a Discord CDN, extracts text using OCR, and verifies the hash.

    :param image_url: The Discord CDN URL of the image.
    :param display: Whether to display the processed image (default: False).
    :return: Dictionary with verification result (`valid_hash`, `played_time`).
    """
    # ✅ Fetch the image from Discord CDN
    image = await fetch_image_from_cdn(image_url)
    if image is None:
        return {"error": "Image could not be processed"}

    # ✅ Convert to grayscale and invert colors for OCR
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image_inverted = cv2.bitwise_not(image_gray)

    # ✅ Run OCR on the processed image
    start_time = time.time()
    text = pytesseract.image_to_string(image_inverted, lang=model, config=custom_config)
    end_time = time.time()

    logger.debug(f"OCR Extracted Text: {text}")

    # ✅ Extract key-value pairs from OCR text
    data = extract_ocr_data(text)

    if not data:
        logger.error("❌ OCR failed to extract valid data.")
        return {"error": "Invalid format"}

    # ✅ Extract map code, hash, and playtime
    try:
        map_code, provided_hash, played_time = extract_mapcode_hash_playedtime(data.get("hash", ""), data.get("played time (in minutes)", 0))
    except ValueError as e:
        logger.error(f"❌ Error processing proof: {e}")
        return {"error": "Incomplete or incorrect data"}
    

    if map_code is None or provided_hash is None or played_time == 0:
        logger.error("❌ Invalid data format detected.")
        return {"error": "Incomplete or incorrect data"}

    # ✅ Verify hash
    valid_hash = verify_hash(map_code, played_time, provided_hash)

    logger.info(f"Hash Verification Result: {valid_hash}")
    logger.info(f"OCR Inference Time: {end_time - start_time:.3f} seconds")
    logger.info("----------")

    if display:
        #plt.imshow(image_inverted, cmap='gray')
        #plt.axis('off')
        #plt.show()
        pass

    return {
        "valid_hash": valid_hash,
        "played_time": played_time
    }

def extract_ocr_data(text):
    """
    Parses the OCR text and extracts key-value pairs.

    :param text: The OCR-extracted text.
    :return: Dictionary with extracted key-value pairs.
    """
    data = {}
    for line in text.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            key = find_best_key_match(parts[0].strip())
            value = parts[1].strip()
            if key:
                data[key] = value

    logger.debug(f"Extracted Data: {data}")
    return data

def find_best_key_match(ocr_key):
    """
    Finds the closest match for the OCR-detected key from the expected keys.

    :param ocr_key: The key detected by OCR.
    :return: The best-matched key if confidence is high enough, else None.
    """
    best_match, score = process.extractOne(ocr_key.lower(), EXPECTED_KEYS)
    return best_match if score >= 80 else None  # Adjust threshold if needed

def extract_mapcode_hash_playedtime(proof_string, playedtime_string):
    """
    Extracts the map code and hash value from the proof string.

    :param proof_string: The extracted proof string (expected format: "MapCodeXHashValue").
    :return: Tuple (map_code, hash_value) or (None, None) if invalid.
    """
    try:
        parts = proof_string.split("X")
        if len(parts) != 2:
            raise ValueError("Invalid proof format. Expected format: 'MapCodeXHashValue'")
        
        # Keep only digits (manual filtering)
        map_code = int("".join(c for c in parts[0] if c in "0123456789"))
        hash_value = int("".join(c for c in parts[1] if c in "0123456789"))
        played_time = int("".join(c for c in playedtime_string if c in "0123456789"))
        
        return map_code, hash_value, played_time
    except ValueError as e:
        logger.error(f"❌ Error processing proof: {e} | Received: {proof_string}")
        return None, None, None

def verify_hash(map_code, play_time, provided_hash):
    """
    Verifies whether the provided hash matches the expected calculated hash.

    :param map_code: The extracted map code.
    :param play_time: The extracted play time.
    :param provided_hash: The extracted hash value.
    :return: True if the hash is valid, False otherwise.
    """
    calculated_hash = ((map_code * 134569 + play_time * 456781) + int(SECRET_TIMETRACKER_KEY)) % 3456789
    return calculated_hash == provided_hash

# ✅ TESTING
if __name__ == "__main__":
    test_image_url = "https://cdn.discordapp.com/attachments/1335408542479286384/1351319742912135188/Screenshot_2025-03-16_175343.png?ex=67d9f215&is=67d8a095&hm=2d33f0ffca72ef984d18e678545ea8f4df1806ac1a26704514de7f167556bbea&"  # Example CDN URL

    async def run_test():
        result = await check_image(test_image_url, display=False)
        logger.info(f"Test Result: {result}")

    
    asyncio.run(run_test())

    print(pytesseract.pytesseract.tesseract_cmd)
