"""MediaPipe Pose によるリアルタイムランドマーク取得。

streamlit-webrtc の VideoProcessorBase を継承し、
recv() 内で毎フレーム推論 → ロング形式バッファに蓄積する。
"""
import threading
import time

import av
import cv2
import mediapipe as mp
import pandas as pd

# streamlit-webrtc のバージョンによってクラス名が異なるため両対応にする。
# 0.47 系では VideoProcessorBase、それ以前は VideoTransformerBase。
try:
    from streamlit_webrtc import VideoProcessorBase
except ImportError:  # pragma: no cover - 古いバージョン向けフォールバック
    from streamlit_webrtc import VideoTransformerBase as VideoProcessorBase


# ロング形式 DataFrame の列（calculate_metrics_by_frame が要求する形式）
_LONG_COLUMNS = ["frame", "landmark_index", "x", "y", "z", "visibility"]


class PoseCaptureProcessor(VideoProcessorBase):
    """カメラフレームから MediaPipe ランドマークを抽出するプロセッサ。

    蓄積データはロング形式（1行=1ランドマーク点）:
      frame, landmark_index, x, y, z, visibility

    使い方:
      1. webrtc_streamer の video_processor_factory に渡す
      2. 計測開始時に start_capture() を呼ぶ
      3. 計測終了時に stop_capture() を呼ぶ
      4. get_dataframe() でロング形式 DataFrame を取得
    """

    def __init__(self):
        """内部状態を初期化し、MediaPipe Pose モデルをロードする。"""
        self._lock = threading.Lock()
        self._capturing = False
        self._buffer = []       # list of dict
        self._frame_idx = 0
        self._start_time = None
        self._end_time = None

        # MediaPipe Pose 初期化（軽量モード）
        # model_complexity=1: 精度と速度のバランスが良い中間モデル（0=軽量, 2=高精度）を採用。
        # confidence 系はいずれも 0.5: デフォルト推奨値で誤検出と未検出のバランスを取る。
        self._pose = mp.solutions.pose.Pose(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._mp_drawing = mp.solutions.drawing_utils
        self._mp_pose = mp.solutions.pose

    def start_capture(self):
        """計測区間の開始。バッファをリセットして蓄積を開始する。"""
        with self._lock:
            self._buffer = []
            self._frame_idx = 0
            self._start_time = time.time()
            self._end_time = None
            self._capturing = True

    def stop_capture(self):
        """計測区間の終了。蓄積を停止する。"""
        with self._lock:
            self._capturing = False
            self._end_time = time.time()

    @property
    def is_capturing(self) -> bool:
        """現在ランドマークを蓄積中かどうかを返す。"""
        with self._lock:
            return self._capturing

    def get_dataframe(self) -> pd.DataFrame:
        """蓄積したランドマークをロング形式 DataFrame で返す。

        calculate_metrics_by_frame() にそのまま渡せる形式。
        df.attrs["fps"] に実測 fps を格納する。
        """
        with self._lock:
            if not self._buffer:
                return pd.DataFrame(columns=_LONG_COLUMNS)
            df = pd.DataFrame(self._buffer)

            # 実測 fps を計算して attrs に格納
            if self._start_time and self._end_time:
                elapsed = self._end_time - self._start_time
            elif self._start_time:
                elapsed = time.time() - self._start_time
            else:
                elapsed = 1.0

            n_frames = df["frame"].nunique()
            fps = n_frames / max(elapsed, 0.001)
            df.attrs["fps"] = fps
            return df

    @property
    def frame_count(self) -> int:
        """これまでに蓄積したフレーム数（ランドマーク検出できたフレームのみ）を返す。"""
        with self._lock:
            return self._frame_idx

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        """毎フレーム呼ばれるコールバック（別スレッド実行）。

        1. OpenCV 画像に変換
        2. MediaPipe Pose で推論
        3. 骨格を映像に描画（ユーザーへのフィードバック）
        4. _capturing 中はランドマークをバッファに蓄積
        5. 映像を返す
        """
        img = frame.to_ndarray(format="bgr24")
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        results = self._pose.process(img_rgb)

        if results.pose_landmarks:
            # 骨格描画（常に表示）
            self._mp_drawing.draw_landmarks(
                img,
                results.pose_landmarks,
                self._mp_pose.POSE_CONNECTIONS,
            )

            # 計測中のみバッファに蓄積（カウントダウン中は蓄積しない）
            with self._lock:
                if self._capturing:
                    for i, lm in enumerate(results.pose_landmarks.landmark):
                        self._buffer.append({
                            "frame": self._frame_idx,
                            "landmark_index": i,
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z,
                            "visibility": lm.visibility,
                        })
                    self._frame_idx += 1

        # 左右反転（鏡像・現行 JS カメラと同じ見た目）
        img = cv2.flip(img, 1)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

    def __del__(self):
        """インスタンス破棄時に MediaPipe Pose モデルのリソースを解放する。"""
        if hasattr(self, "_pose"):
            self._pose.close()
