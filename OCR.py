import os
import numpy as np
from PIL import Image
import pytesseract

class ImageTextExtractor:
    def __init__(self, image_path):
        self.image_path = image_path

    def extract_text(self):
        if not os.path.exists(self.image_path):
            print(f"Image file not found: {self.image_path}")
            return ""

        try:
            image = Image.open(self.image_path).convert('RGB')
            image = self._trim_whitespace(image)
        except Exception as e:
            print(f"Failed to open image: {str(e)}")
            return ""

        parts = self._segment_letters_by_projection(image)

        extracted_text = []
        for idx, part in enumerate(parts):
            print(f"Processing part {idx+1}")
            ch = self._recognize_with_rotations(part)
            extracted_text.append(ch)

        return "".join(extracted_text).replace(' ', '').strip()

    def _trim_whitespace(self, image):
        img_array = np.asarray(image)
        is_white = np.all(img_array == [255,255,255], axis=-1)
        rows = np.where(~np.all(is_white, axis=1))[0]
        cols = np.where(~np.all(is_white, axis=0))[0]
        if rows.size == 0 or cols.size == 0:
            return image
        top, bottom = rows[0], rows[-1]+1
        left, right   = cols[0], cols[-1]+1
        return image.crop((left, top, right, bottom))

    def _segment_letters_by_projection(self, image):
        gray = image.convert('L')
        arr = np.array(gray)
        binary = np.where(arr < 32, 0, 255)
        vsum = np.sum(binary==0, axis=0)

        parts, start = [], None
        for x, count in enumerate(vsum):
            if count>0 and start is None:
                start = x
            elif count==0 and start is not None:
                if x-start >= 5:
                    parts.append(image.crop((start,0,x,image.height)))
                start = None

        if start is not None and (len(vsum)-start)>=5:
            parts.append(image.crop((start,0,len(vsum),image.height)))

        print(f"Segmented into {len(parts)} letter parts")
        return parts

    def _recognize_with_rotations(
        self,
        image: Image.Image,
        whitelist: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ) -> str:
        """
        Rotate `image` through the specific angles [-30, -15, 15, 30],
        OCR each with Tesseract (PSM 10, uppercase only), and return the highest‐confidence char.
        """
        best_char, best_conf = "", -1.0

        # only these four angles
        angles = [-30, -15, 15, 30]

        tconfig = f"-c tessedit_char_whitelist={whitelist} --psm 10 --oem 3"

        for ang in angles:
            # rotate and pad with white
            rot = image.rotate(ang, expand=True, fillcolor=(255,255,255))
            data = pytesseract.image_to_data(
                rot, config=tconfig, output_type=pytesseract.Output.DICT
            )

            # scan until we find a non‐empty text result
            for txt, conf in zip(data["text"], data["conf"]):
                txt = txt.strip()
                if not txt:
                    continue
                try:
                    c_conf = float(conf)
                except Exception:
                    continue

                if c_conf > best_conf:
                    best_conf, best_char = c_conf, txt
                break  # only consider the first detected character

        return best_char



