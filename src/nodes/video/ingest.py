"""
YeyoOS — Video Ingest Pipeline
Extrae frames de un video, corre MediaPipe Pose Estimation (Tasks API),
segmenta por acción y genera memorias en video:acciones_humanas.

Pipeline: RECEIVED → FRAME_EXTRACT → POSE_ESTIMATE → ACTION_SEGMENT → EMBEDDING → STORED
"""

import asyncio
import logging
import math
import tempfile
from pathlib import Path
from dataclasses import dataclass, field

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmarker, PoseLandmarkerOptions, PoseLandmark, RunningMode,
)

from src.memory.pipeline_events import pipeline_buffer

logger = logging.getLogger("yeyoos.video.ingest")

# Model path — downloaded on first use
MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "pose_landmarker_lite.task"

# Key joints for action classification
KEY_JOINTS = {
    PoseLandmark.LEFT_SHOULDER, PoseLandmark.RIGHT_SHOULDER,
    PoseLandmark.LEFT_ELBOW, PoseLandmark.RIGHT_ELBOW,
    PoseLandmark.LEFT_WRIST, PoseLandmark.RIGHT_WRIST,
    PoseLandmark.LEFT_HIP, PoseLandmark.RIGHT_HIP,
    PoseLandmark.LEFT_KNEE, PoseLandmark.RIGHT_KNEE,
    PoseLandmark.LEFT_ANKLE, PoseLandmark.RIGHT_ANKLE,
}


@dataclass
class PoseFrame:
    """Pose data for a single frame."""
    frame_idx: int
    timestamp_sec: float
    landmarks: dict[str, tuple[float, float, float]]  # joint_name -> (x, y, z)
    confidence: float


@dataclass
class ActionSegment:
    """A segment of contiguous action."""
    start_sec: float
    end_sec: float
    action_label: str
    avg_confidence: float
    key_poses: list[dict]
    frame_count: int


@dataclass
class IngestResult:
    """Result of video ingestion."""
    video_path: str
    total_frames: int
    fps: float
    duration_sec: float
    poses_extracted: int
    segments: list[ActionSegment]
    memories_stored: int = 0


class VideoIngestPipeline:
    """
    Ingests reference videos to build the video:acciones_humanas memory bank.
    Uses MediaPipe Pose Landmarker (Tasks API) to extract body landmarks.
    """

    SAMPLE_FPS = 4
    MIN_SEGMENT_SEC = 0.5
    MOVEMENT_THRESHOLD = 0.03

    def __init__(self, memory_service=None):
        self._memory_service = memory_service

    async def ingest(self, video_path: str, label_hint: str = "") -> IngestResult:
        """Full ingest pipeline."""
        pid = pipeline_buffer.new_pipeline(source="video_ingest")
        pipeline_buffer.emit(pid, "RECEIVED", "ok",
                             f"Video: {Path(video_path).name}",
                             {"path": video_path, "label": label_hint})

        # Step 1: Extract metadata
        logger.info(f"[ingest] Extrayendo frames de {video_path}")
        meta = await asyncio.get_event_loop().run_in_executor(
            None, self._get_video_meta, video_path
        )
        if not meta:
            pipeline_buffer.emit(pid, "FRAME_EXTRACT", "error", "No se pudo abrir el video")
            return IngestResult(video_path, 0, 0, 0, 0, [])

        total_frames, fps, duration = meta["total"], meta["fps"], meta["duration"]
        pipeline_buffer.emit(pid, "FRAME_EXTRACT", "ok",
                             f"{total_frames} frames, {fps:.1f} FPS, {duration:.1f}s")

        # Step 2: Pose estimation
        logger.info(f"[ingest] Estimando poses (sample {self.SAMPLE_FPS} fps)")
        poses = await asyncio.get_event_loop().run_in_executor(
            None, self._estimate_poses, video_path, fps
        )
        pipeline_buffer.emit(pid, "POSE_ESTIMATE",
                             "ok" if poses else "error",
                             f"{len(poses)} poses extraídas" if poses else "Sin poses detectadas")

        if not poses:
            return IngestResult(video_path, total_frames, fps, duration, 0, [])

        # Step 3: Segment by action
        logger.info(f"[ingest] Segmentando {len(poses)} poses en acciones")
        segments = self._segment_actions(poses, label_hint)
        pipeline_buffer.emit(pid, "ACTION_SEGMENT", "ok",
                             f"{len(segments)} segmentos detectados",
                             {"segments": [s.action_label for s in segments]})

        # Step 4: Store as memories
        memories_stored = 0
        if self._memory_service and segments:
            for seg in segments:
                content = self._segment_to_memory_text(seg, video_path)
                metadata = {
                    "source_video": Path(video_path).name,
                    "action": seg.action_label,
                    "start_sec": seg.start_sec,
                    "end_sec": seg.end_sec,
                    "duration_sec": round(seg.end_sec - seg.start_sec, 2),
                    "confidence": round(seg.avg_confidence, 3),
                    "frame_count": seg.frame_count,
                }
                stored = await self._memory_service.store_result(
                    content=content,
                    namespace="video:acciones_humanas",
                    memory_type="skill",
                    source="video_ingest",
                    metadata=metadata,
                    _pipeline_id=pid if memories_stored == 0 else None,
                )
                if stored:
                    memories_stored += 1

        if memories_stored == 0:
            pipeline_buffer.emit(pid, "EMBEDDING", "skip", "Sin memorias que guardar")
            pipeline_buffer.emit(pid, "STORED", "skip", "Sin memorias que guardar")

        logger.info(f"[ingest] ✅ {memories_stored} memorias de {len(segments)} segmentos")
        return IngestResult(video_path, total_frames, fps, duration, len(poses), segments, memories_stored)

    def _get_video_meta(self, video_path: str) -> dict | None:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total / fps if fps > 0 else 0
        cap.release()
        return {"total": total, "fps": fps, "duration": duration}

    def _estimate_poses(self, video_path: str, video_fps: float) -> list[PoseFrame]:
        """Run MediaPipe Pose Landmarker on sampled frames."""
        if not MODEL_PATH.exists():
            logger.error(f"[ingest] Pose model not found: {MODEL_PATH}")
            return []

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        poses: list[PoseFrame] = []
        frame_skip = max(1, int(video_fps / self.SAMPLE_FPS))

        with PoseLandmarker.create_from_options(options) as landmarker:
            cap = cv2.VideoCapture(video_path)
            frame_idx = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_skip == 0:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    timestamp_ms = int(frame_idx / video_fps * 1000)

                    result = landmarker.detect_for_video(mp_image, timestamp_ms)

                    if result.pose_landmarks and len(result.pose_landmarks) > 0:
                        lms = result.pose_landmarks[0]
                        landmarks = {}
                        confidences = []
                        for lm_enum in PoseLandmark:
                            idx = lm_enum.value
                            if idx < len(lms):
                                lm = lms[idx]
                                landmarks[lm_enum.name.lower()] = (lm.x, lm.y, lm.z)
                                confidences.append(lm.visibility if hasattr(lm, 'visibility') else 0.8)

                        avg_conf = sum(confidences) / len(confidences) if confidences else 0
                        poses.append(PoseFrame(
                            frame_idx=frame_idx,
                            timestamp_sec=frame_idx / video_fps,
                            landmarks=landmarks,
                            confidence=avg_conf,
                        ))

                frame_idx += 1
            cap.release()

        return poses

    def _segment_actions(self, poses: list[PoseFrame], label_hint: str) -> list[ActionSegment]:
        """Segment poses into action chunks based on movement velocity."""
        if len(poses) < 2:
            if poses:
                return [ActionSegment(
                    start_sec=poses[0].timestamp_sec,
                    end_sec=poses[0].timestamp_sec + 0.5,
                    action_label=label_hint or "static_pose",
                    avg_confidence=poses[0].confidence,
                    key_poses=[self._pose_to_dict(poses[0])],
                    frame_count=1,
                )]
            return []

        velocities = [self._pose_delta(poses[i - 1], poses[i]) for i in range(1, len(poses))]

        segments: list[ActionSegment] = []
        seg_start = 0
        is_moving = velocities[0] > self.MOVEMENT_THRESHOLD

        for i in range(1, len(velocities)):
            current_moving = velocities[i] > self.MOVEMENT_THRESHOLD
            if current_moving != is_moving:
                seg_poses = poses[seg_start:i + 1]
                seg = self._build_segment(seg_poses, is_moving, label_hint)
                if seg.end_sec - seg.start_sec >= self.MIN_SEGMENT_SEC:
                    segments.append(seg)
                seg_start = i
                is_moving = current_moving

        seg_poses = poses[seg_start:]
        seg = self._build_segment(seg_poses, is_moving, label_hint)
        if seg.end_sec - seg.start_sec >= self.MIN_SEGMENT_SEC:
            segments.append(seg)

        return segments

    def _pose_delta(self, p1: PoseFrame, p2: PoseFrame) -> float:
        key_names = {j.name.lower() for j in KEY_JOINTS}
        deltas = []
        for joint in key_names:
            if joint in p1.landmarks and joint in p2.landmarks:
                x1, y1, _ = p1.landmarks[joint]
                x2, y2, _ = p2.landmarks[joint]
                deltas.append(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
        return sum(deltas) / len(deltas) if deltas else 0.0

    def _build_segment(self, poses: list[PoseFrame], is_moving: bool, label_hint: str) -> ActionSegment:
        label = label_hint or ("movement" if is_moving else "static")
        if not is_moving and label_hint:
            label = f"{label_hint}_hold"

        sample_indices = [0, len(poses) // 2, -1] if len(poses) >= 3 else list(range(len(poses)))
        key_poses = [self._pose_to_dict(poses[i]) for i in sample_indices if abs(i) < len(poses)]
        avg_conf = sum(p.confidence for p in poses) / len(poses)

        return ActionSegment(
            start_sec=poses[0].timestamp_sec,
            end_sec=poses[-1].timestamp_sec,
            action_label=label,
            avg_confidence=avg_conf,
            key_poses=key_poses,
            frame_count=len(poses),
        )

    def _pose_to_dict(self, pose: PoseFrame) -> dict:
        key_names = {j.name.lower() for j in KEY_JOINTS}
        return {
            "timestamp": round(pose.timestamp_sec, 3),
            "confidence": round(pose.confidence, 3),
            "joints": {
                j: {"x": round(v[0], 4), "y": round(v[1], 4), "z": round(v[2], 4)}
                for j, v in pose.landmarks.items()
                if j in key_names
            },
        }

    def _segment_to_memory_text(self, seg: ActionSegment, video_path: str) -> str:
        duration = round(seg.end_sec - seg.start_sec, 1)
        filename = Path(video_path).stem

        pose_desc = ""
        if seg.key_poses:
            mid = seg.key_poses[len(seg.key_poses) // 2]
            joints = mid.get("joints", {})
            if "left_wrist" in joints and "left_shoulder" in joints:
                if joints["left_wrist"]["y"] < joints["left_shoulder"]["y"]:
                    pose_desc += "brazos elevados, "
                else:
                    pose_desc += "brazos abajo, "
            if "left_knee" in joints and "left_hip" in joints:
                if abs(joints["left_knee"]["y"] - joints["left_hip"]["y"]) < 0.1:
                    pose_desc += "piernas flexionadas, "

        return (
            f"Acción: {seg.action_label} | "
            f"Duración: {duration}s | "
            f"Video: {filename} | "
            f"Frames: {seg.frame_count} | "
            f"Confianza: {seg.avg_confidence:.0%} | "
            f"{pose_desc.rstrip(', ')}"
        )
