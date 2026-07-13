"""
Audio Video Sync - ComfyUI Custom Node
연결된 AUDIO의 길이(샘플 수/샘플레이트)만 보고, 24fps부터 시작해서
정확히(나머지 없이) 나누어지는 fps를 자동으로 찾아 FPS/DURATION/FRAMES를
출력한다. 24fps에서 딱 맞지 않으면 23, 22, ... 순으로 낮춰가며 맞는
fps를 찾는다. 사용자가 fps를 직접 입력할 필요는 없다.
"""


class AudioVideoSync:
    MAX_FPS = 24
    MIN_FPS = 1

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "INT")
    RETURN_NAMES = ("fps", "duration", "frames")
    FUNCTION = "compute"
    CATEGORY = "audio"

    def compute(self, audio):
        waveform = audio["waveform"]
        sample_rate = audio["sample_rate"]
        num_samples = int(waveform.shape[-1])
        duration = num_samples / sample_rate

        # num_samples, sample_rate 모두 정수이므로, (num_samples * fps)가
        # sample_rate로 나머지 없이 나누어지면 frames/fps는 duration과
        # 부동소수점 오차 없이 정확히 같다. 24fps부터 내려가며 그런 fps를 찾는다.
        chosen_fps = None
        chosen_frames = None
        for fps in range(self.MAX_FPS, self.MIN_FPS - 1, -1):
            if (num_samples * fps) % sample_rate == 0:
                chosen_fps = fps
                chosen_frames = (num_samples * fps) // sample_rate
                break

        if chosen_fps is not None:
            print(
                f"[AudioVideoSync] 오디오 길이 {duration:.4f}s -> {chosen_fps}fps에서 정확히 일치 "
                f"(frames={chosen_frames})"
            )
        else:
            # MIN_FPS~MAX_FPS 범위에 정확히 맞는 값이 없으면 24fps 기준 근사값으로 대체
            chosen_fps = self.MAX_FPS
            chosen_frames = max(1, round(duration * chosen_fps))
            error_ms = abs(chosen_frames / chosen_fps - duration) * 1000
            print(
                f"[AudioVideoSync] ⚠ {self.MIN_FPS}~{self.MAX_FPS}fps 범위에서 정확히 일치하는 값을 "
                f"찾지 못해 {chosen_fps}fps 근사값 사용 (frames={chosen_frames}, 오차 {error_ms:.2f}ms)"
            )

        return (float(chosen_fps), duration, chosen_frames)


NODE_CLASS_MAPPINGS = {
    "nambaksa_audio_video_sync": AudioVideoSync,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "nambaksa_audio_video_sync": "Audio to Video FPS/Frames",
}
