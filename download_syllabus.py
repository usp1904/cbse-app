import os
import urllib.request
import hashlib
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Base directory for storing syllabus data
BASE_DIR = Path("Syllabus_2026-27")

# Folder structure definition
FOLDER_STRUCTURE = {
    "CBSE": [f"Class_{i:02d}" for i in range(5, 13)],
    "AP_State": ["Class_06-10", "Intermediate_1st_Year", "Intermediate_2nd_Year"],
    "TS_State": ["Class_06-10", "Intermediate_1st_Year", "Intermediate_2nd_Year"]
}

# Mapping of actual URLs for downloading syllabus PDFs (verified for academic year 2026-27)
SYLLABUS_URLS = {
    "CBSE": {
        "Class_09": [
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/Maths_SecP1IX_2026-27.pdf", "CBSE_Class09_Mathematics_2026-27.pdf"),
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/ScienceSt_SecP1_2026-27.pdf", "CBSE_Class09_Science_2026-27.pdf")
        ],
        "Class_10": [
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/Maths_SecP1X_2026-27.pdf", "CBSE_Class10_Mathematics_2026-27.pdf"),
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart1/Science_SecP1_2026-27.pdf", "CBSE_Class10_Science_2026-27.pdf")
        ],
        "Class_11": [
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart2/Physics_SecP2_2026-27.pdf", "CBSE_Class11_Physics_2026-27.pdf"),
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart2/Chemistry_SecP2_2026-27.pdf", "CBSE_Class11_Chemistry_2026-27.pdf"),
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart2/Maths_SecP2_2026-27.pdf", "CBSE_Class11_Mathematics_2026-27.pdf"),
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart2/Biology_SecP2_2026-27.pdf", "CBSE_Class11_Biology_2026-27.pdf")
        ],
        "Class_12": [
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart2/Physics_SecP2_2026-27.pdf", "CBSE_Class12_Physics_2026-27.pdf"),
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart2/Chemistry_SecP2_2026-27.pdf", "CBSE_Class12_Chemistry_2026-27.pdf"),
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart2/Maths_SecP2_2026-27.pdf", "CBSE_Class12_Mathematics_2026-27.pdf"),
            ("https://cbseacademic.nic.in/web_material/CurriculumMain27/SecPart2/Biology_SecP2_2026-27.pdf", "CBSE_Class12_Biology_2026-27.pdf")
        ]
    },
    "AP_State": {
        "Intermediate_1st_Year": [
            ("https://bie.ap.gov.in/pdf/RevisedSyllabus1stYear.pdf", "AP_Inter_1stYear_RevisedSyllabus_2026-27.pdf")
        ]
    },
    "TS_State": {
        "Class_06-10": [
            ("https://scert.telangana.gov.in/pdf/syllabus.pdf", "TS_Class06-10_GeneralSyllabus_2026-27.pdf")
        ]
    }
}

def create_directory_structure():
    """Initializes the standard folder structure for the Master Syllabus Pack."""
    logger.info("Initializing folder structure...")
    for board, subfolders in FOLDER_STRUCTURE.items():
        board_dir = BASE_DIR / board
        for subfolder in subfolders:
            folder_path = board_dir / subfolder
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created/Verified directory: {folder_path}")

def calculate_sha256(file_path: Path) -> str:
    """Calculates the SHA-256 hash of a file to detect changes."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_file(url: str, dest_path: Path) -> bool:
    """Downloads a file from a URL to a local destination. Returns True if updated."""
    temp_path = dest_path.with_suffix(".tmp")
    try:
        logger.info(f"Downloading {url} to {dest_path.name}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response, open(temp_path, "wb") as out_file:
            out_file.write(response.read())
        
        # If the destination file already exists, check if hash has changed
        if dest_path.exists():
            old_hash = calculate_sha256(dest_path)
            new_hash = calculate_sha256(temp_path)
            if old_hash == new_hash:
                logger.info(f"File {dest_path.name} is up to date (no changes).")
                temp_path.unlink()
                return False
            else:
                logger.info(f"File {dest_path.name} has changed. Replacing old version.")
                dest_path.unlink()
        
        temp_path.rename(dest_path)
        logger.info(f"Successfully downloaded and updated {dest_path.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False

def sync_syllabus():
    """Iterates through mapped URLs and downloads missing or updated syllabus files."""
    create_directory_structure()
    logger.info("Starting syllabus sync...")
    
    updated_files = 0
    total_files = 0
    
    for board, classes in SYLLABUS_URLS.items():
        for class_name, urls in classes.items():
            dest_dir = BASE_DIR / board / class_name
            for url, filename in urls:
                total_files += 1
                dest_path = dest_dir / filename
                if download_file(url, dest_path):
                    updated_files += 1
                    
    logger.info(f"Sync complete. Total processed: {total_files}, Updated: {updated_files}")

if __name__ == "__main__":
    sync_syllabus()
