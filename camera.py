"""Camera + hand- óf lijftracking.

Twee threads, losgekoppeld zodat het beeld op volle 30 fps blijft terwijl de
detectie (~30 ms per frame) in zijn eigen tempo draait:

- capture-thread: leest MJPG 1280x720@30 van de webcam, spiegelt, en legt het
  nieuwste RGB-frame klaar.
- inference-thread: pakt telkens het nieuwste frame, verkleint naar 480x270 en
  draait MediaPipe. Per spelmodus draait er precies één model: HandLandmarker
  (handspellen, menu) of PoseLandmarker (lijfspellen zoals Vliegende draak) —
  allebei tegelijk zou de detectie onder de 30 Hz drukken.

Gotcha's van deze webcam (zie geheugen): exposure_dynamic_framerate halveert
naar 15 fps → uitzetten; CAP_PROP_BUFFERSIZE=1 halveert óók → niet zetten.
"""
import math
import subprocess
import threading
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

from body import Body, BodyTracker

CAM_W, CAM_H = 1280, 720
INFER_W, INFER_H = 480, 270

# MediaPipe-landmarknummers: vingertoppen + punten die samen de palm vormen
TIP_IDS = [4, 8, 12, 16, 20]
PALM_IDS = [0, 5, 9, 13, 17]


@dataclass
class Hand:
    tips: list  # 5 × (nx, ny) genormaliseerd, al gespiegeld
    palm: tuple
    openness: float = 2.0  # ~2.0 = open hand, ~1.1 = vuist
    t: float = field(default_factory=time.time)


class CameraTracker:
    def __init__(self, model_path: str, pose_model_path: str | None = None,
                 device: str = "/dev/video0") -> None:
        self._fix_camera_controls(device)
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        if not self.cap.isOpened():
            raise RuntimeError("Kan de webcam niet openen")

        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        self._mp_image_cls = None
        import mediapipe as mp
        self._mp = mp
        self.landmarker = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=mpp.BaseOptions(model_asset_path=model_path),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=4,  # twee kinderen tegelijk voor het scherm
                min_hand_detection_confidence=0.4,
                min_tracking_confidence=0.4,
            )
        )
        self.pose_landmarker = None
        if pose_model_path:
            self.pose_landmarker = vision.PoseLandmarker.create_from_options(
                vision.PoseLandmarkerOptions(
                    base_options=mpp.BaseOptions(model_asset_path=pose_model_path),
                    running_mode=vision.RunningMode.VIDEO,
                    num_poses=1,  # het grootste kind in beeld stuurt
                    min_pose_detection_confidence=0.4,
                    min_tracking_confidence=0.4,
                )
            )
        self.body_tracker = BodyTracker()

        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None  # RGB, gespiegeld, CAM_W x CAM_H
        self._frame_id = 0
        self._hands: list[Hand] = []
        self._track = "hands"  # "hands" of "body", per spelmodus
        self._running = True
        self.capture_fps = 0.0
        self.infer_fps = 0.0

        self._threads = [
            threading.Thread(target=self._capture_loop, daemon=True),
            threading.Thread(target=self._infer_loop, daemon=True),
        ]
        for t in self._threads:
            t.start()

    @staticmethod
    def _fix_camera_controls(device: str) -> None:
        try:
            subprocess.run(
                ["v4l2-ctl", "-d", device, "--set-ctrl=exposure_dynamic_framerate=0"],
                capture_output=True, timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass  # zonder v4l2-ctl draait het ook, alleen mogelijk op 15 fps

    def _capture_loop(self) -> None:
        n, t0 = 0, time.time()
        while self._running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            frame = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
            with self._lock:
                self._frame = frame
                self._frame_id += 1
            n += 1
            if n == 30:
                now = time.time()
                self.capture_fps = 30 / (now - t0)
                n, t0 = 0, now
        self.cap.release()

    def _infer_loop(self) -> None:
        last_id = 0
        n, t0 = 0, time.time()
        while self._running:
            with self._lock:
                frame, fid = self._frame, self._frame_id
            if frame is None or fid == last_id:
                time.sleep(0.002)
                continue
            last_id = fid
            small = cv2.resize(frame, (INFER_W, INFER_H), interpolation=cv2.INTER_AREA)
            img = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(small))
            if self._track == "body" and self.pose_landmarker is not None:
                try:
                    res = self.pose_landmarker.detect_for_video(img, int(time.time() * 1000))
                except Exception:
                    continue
                if res.pose_landmarks:
                    self.body_tracker.feed(res.pose_landmarks[0])
                n += 1
                if n == 20:
                    now = time.time()
                    self.infer_fps = 20 / (now - t0)
                    n, t0 = 0, now
                continue
            try:
                res = self.landmarker.detect_for_video(img, int(time.time() * 1000))
            except Exception:
                continue
            hands = []
            for lm in res.hand_landmarks:
                tips = [(lm[i].x, lm[i].y) for i in TIP_IDS]
                px = sum(lm[i].x for i in PALM_IDS) / len(PALM_IDS)
                py = sum(lm[i].y for i in PALM_IDS) / len(PALM_IDS)
                # openheid: gemiddelde afstand vingertop→pols, geschaald op
                # pols→middelvinger-knokkel zodat het onafhankelijk is van
                # hoe ver de hand van de camera is
                ref = math.hypot(lm[9].x - lm[0].x, lm[9].y - lm[0].y) or 1e-6
                stretch = sum(math.hypot(lm[i].x - lm[0].x, lm[i].y - lm[0].y)
                              for i in (8, 12, 16, 20)) / 4
                hands.append(Hand(tips=tips, palm=(px, py), openness=stretch / ref))
            with self._lock:
                self._hands = hands
            n += 1
            if n == 20:
                now = time.time()
                self.infer_fps = 20 / (now - t0)
                n, t0 = 0, now

    def get_frame(self) -> tuple[int, np.ndarray | None]:
        with self._lock:
            return self._frame_id, self._frame

    def get_hands(self) -> list[Hand]:
        with self._lock:
            return list(self._hands)

    def set_tracking(self, kind: str) -> None:
        """"hands" of "body" — wisselt welk model de inference-thread draait."""
        with self._lock:
            self._track = kind if self.pose_landmarker is not None else "hands"
            if kind == "body":
                self._hands = []

    def get_body(self) -> Body:
        return self.body_tracker.get()

    def poll_body_events(self) -> list[str]:
        return self.body_tracker.poll_events()

    def stop(self) -> None:
        # netjes afbouwen: eerst de threads laten stoppen, dan het model
        # sluiten — anders kan MediaPipe met een SIGABRT vallen bij exit
        self._running = False
        for t in self._threads:
            t.join(timeout=1.0)
        for lm in (self.landmarker, self.pose_landmarker):
            try:
                if lm is not None:
                    lm.close()
            except Exception:
                pass
