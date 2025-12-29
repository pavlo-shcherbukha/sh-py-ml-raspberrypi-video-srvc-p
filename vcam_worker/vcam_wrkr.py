import os
import time 
import sys
import logging
#import vcam_worker.shjsonformatter
from datetime import datetime,timedelta
#import uuid
import cv2
from azure.storage.blob import BlobServiceClient

RTSP_URL = "rtsp://admin:select@192.168.0.101:8554/live"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
logger = logging.getLogger(__name__)

apploglevel=os.environ.get("LOGLEVEL")
if apploglevel==None:
    logger.setLevel(logging.DEBUG)
elif apploglevel=='DEBUG':
    logger.setLevel(logging.DEBUG)    
elif apploglevel=='INFO':
    logger.setLevel(logging.INFO)    
elif apploglevel=='WARNING':
    logger.setLevel(logging.WARNING)    
elif apploglevel=='ERROR':    
    logger.setLevel(logging.ERROR)    
elif apploglevel=='CRITICAL':
    logger.setLevel(logging.CRITICAL)    
else:
    logger.setLevel(logging.DEBUG)  

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
if not logger.handlers:
    logger.addHandler(stream_handler)

logger.debug("debug message")
RTSP_URL = os.environ.get('RTSP_URL', 'NONE')
AZ_STRG_CONNSTR = os.environ.get("AZ_STORAGE_CONNSTRING", "NONE")
AZ_STRG_CONTAINER_NAME = os.environ.get("AZ_CONTAINER_NAME", "NONE")

logger.debug( f"===================================")
if RTSP_URL == "NONE":
    logger.debug( f"Не вказано URL rtsp камери")
if AZ_STRG_CONNSTR == "NONE":
    logger.debug( f"Не вказано connectstring до BlobStorage")
if AZ_STRG_CONTAINER_NAME == "NONE":
    logger.debug( f"Не вказано найменування контейнера на BlobStorage")
logger.debug( f"===================================")


def upload_to_azure_blob(file_path, blob_name):
    """
    Завантажує файл у Azure Blob Storage.
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZ_STRG_CONNSTR)
        container_client = blob_service_client.get_container_client(AZ_STRG_CONTAINER_NAME)

        if not container_client.exists():
            container_client.create_container()

        blob_client = container_client.get_blob_client(blob_name)

        logger.debug(f"\nЗавантаження файлу {file_path} до блобу {blob_name}...")
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data)
        logger.debug("Завантаження завершено!")
        return True
    except Exception as ex:
        logger.debug('Виникла помилка під час завантаження:', ex)
        return False



def main():
    """
    Головна функція обробника
    """
    logger.debug("Читаю налаштування")
    while True:
        logging.info("Спроба підключення до RTSP потоку...")
        cap = cv2.VideoCapture(RTSP_URL)
        
        if cap.isOpened():
            logging.info("З'єднання встановлено успішно.")
            # --- Ініціалізація для запису відео ---
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = None
            is_recording = False
            recording_start_time = None
            RECORDING_DURATION = 30 # Запис 30 секунд

            # --- Ініціалізація детектора фону ---
            fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=False)
            MIN_AREA = 5000 # Мінімальна площа для виявлення руху

            while True:
                ret, frame = cap.read()
                if not ret:
                    logging.warning("Потік перервався. Спроба перепідключення...")
                    break
                
                # Викликаємо функцію обробки
                # Застосовуємо алгоритм віднімання фону
                fgmask = fgbg.apply(frame)
                
                # Видаляємо шум та знаходимо контури
                fgmask = cv2.erode(fgmask, None, iterations=2)
                fgmask = cv2.dilate(fgmask, None, iterations=2)
                contours, _ = cv2.findContours(fgmask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                motion_detected = False
                
                for contour in contours:
                    if cv2.contourArea(contour) < MIN_AREA:
                        continue
                    
                    motion_detected = True
                    (x, y, w, h) = cv2.boundingRect(contour)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                # Логіка запису
                if motion_detected and not is_recording:
                    logger.debug("Рух виявлено! Початок запису.")
                    is_recording = True
                    recording_start_time = time.time()
                    current_filename = time.strftime("%Y%m%d-%H%M%S") + ".avi"
                    out = cv2.VideoWriter(current_filename, fourcc, 20.0, (frame.shape[1], frame.shape[0]))
                
                if is_recording:
                    out.write(frame)
                    if time.time() - recording_start_time >= RECORDING_DURATION:
                        out.release()
                        is_recording = False
                        logger.debug("Запис завершено.")
                        if upload_to_azure_blob(current_filename, current_filename):
                            os.remove(current_filename)
                            logger.debug(f"Локальний файл {current_filename} видалено.")     
                # ВАЖЛИВО: У headless режимі cv2.waitKey(1) не потрібен для виводу зображення,
                # але він може бути потрібен для ініціалізації внутрішніх буферів OpenCV.
                # Якщо обробка дуже швидка, можна додати невелику паузу, щоб не вантажити CPU.
                # time.sleep(0.01) 
                
            cap.release()
        else:
            logging.error("Камера недоступна. Наступна спроба через 10 секунд.")
            time.sleep(10)



