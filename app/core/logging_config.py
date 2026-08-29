import logging
import os

def logging_config():
    
    os.makedirs("app/logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
         handlers=[
            logging.FileHandler("app/logs/nexus.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )