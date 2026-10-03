import os
import cv2
import numpy as np


class FridgeVisionProcessor:
    def __init__(self, output_dir: str = "outputs/detections"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _has_circular_cap(self, roi_bgr: np.ndarray) -> bool:
        """
        Validates the presence of a distinct circular white cap inside the bounding box.
        Rejects random light reflections and glare streaks on plastic bags.
        """
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        # 1. Mask for bright white areas
        hsv_roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        white_mask = (hsv_roi[:, :, 1] < 70) & (hsv_roi[:, :, 2] > 175)
        white_uint = (white_mask * 255).astype(np.uint8)

        # 2. Check circularity of white contours
        white_contours, _ = cv2.findContours(white_uint, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for wc in white_contours:
            c_area = cv2.contourArea(wc)
            # Cap must be reasonably sized relative to the carton face
            if (0.02 * w * h) < c_area < (0.35 * w * h):
                perimeter = cv2.arcLength(wc, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * (c_area / (perimeter * perimeter))
                    # Circular caps have circularity > 0.65; glare streaks are < 0.50
                    if circularity > 0.65:
                        return True

        # 3. Fallback: Hough Circle Transform
        blurred = cv2.medianBlur(gray, 5)
        min_radius = int(min(w, h) * 0.08)
        max_radius = int(min(w, h) * 0.35)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=min_radius * 2,
            param1=50,
            param2=22,
            minRadius=min_radius,
            maxRadius=max_radius
        )

        return circles is not None

    def detect_purple_carton(
        self,
        image_path: str,
        output_filename: str = "detected_milk_final.jpg",
        min_area: int = 4000
    ):
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Could not open image at '{image_path}'")

        h_img, w_img = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 1. Narrowed HSV purple window
        lower_purple = np.array([125, 45, 40])
        upper_purple = np.array([155, 255, 255])
        mask = cv2.inRange(hsv, lower_purple, upper_purple)

        # 2. Spatial shelf filter: Ignore the very top shelf zone (bagged produce)
        # Beverages and cartons reside on middle/bottom shelves or door racks
        top_shelf_cutoff = int(h_img * 0.28)
        mask[:top_shelf_cutoff, :] = 0

        # 3. Morphological closing to bridge text and carton seams
        kernel_bridge = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_bridge, iterations=2)
        mask_dilated = cv2.dilate(mask_closed, kernel_bridge, iterations=1)

        contours, _ = cv2.findContours(mask_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        annotated = img.copy()
        valid_detections = []

        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue

            x, y, w, h = cv2.boundingRect(c)
            aspect_ratio = float(h) / w if w > 0 else 0

            # 4. Solidity check (manufactured box vs. organic produce)
            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            solidity = float(area) / hull_area if hull_area > 0 else 0
            extent = float(area) / (w * h) if (w * h) > 0 else 0

            if solidity < 0.85 or extent < 0.55:
                continue

            # 5. Extract ROI and verify genuine circular plastic cap
            roi = img[y:y + h, x:x + w]
            if not self._has_circular_cap(roi):
                continue

            # 6. Orientation
            orientation = "Lying Flat" if aspect_ratio <= 1.35 else "Standing Upright"

            detection = {
                "bbox": (x, y, w, h),
                "area": area,
                "solidity": round(solidity, 2),
                "orientation": orientation
            }
            valid_detections.append(detection)

            # Draw single verified green box
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 3)
            label = f"Tnuva Milk ({orientation})"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(annotated, (x, max(0, y - th - 10)), (x + tw + 8, y), (0, 255, 0), -1)
            cv2.putText(
                annotated,
                label,
                (x + 4, max(th + 2, y - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 0),
                2,
                cv2.LINE_AA
            )

        # 7. Write annotated result to outputs/detections/
        output_filepath = os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_filepath, annotated)

        print(f"\n📦 Verified Detections: {len(valid_detections)}")
        for idx, item in enumerate(valid_detections):
            print(f" [{idx + 1}] BBox: {item['bbox']} | Solidity: {item['solidity']} | Orientation: {item['orientation']}")
        print(f"✅ Clean detection saved to: {output_filepath}\n")

        return valid_detections, annotated


if __name__ == "__main__":
    processor = FridgeVisionProcessor(output_dir="outputs/detections")
    processor.detect_purple_carton(
        image_path="inputs/snapshots/20260501_with_milk.jpg",
        output_filename="detected_milk_final.jpg"
    )