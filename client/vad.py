import queue
import numpy as np
from threading import Thread, Event
from silero-vad-lite import SileroVAD

class VADModule:
    def __init__(self, audio_queue: queue.Queue, on_silence: callable):
        self.audio_queue = audio_queue
        self.on_silence = on_silence
        self.active = True
        self._stop_event = Event()

        self.vad = SileroVAD()
        
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_active(self, is_active: bool):
        self.active = is_active

    def stop(self):
        self._stop_event.set()
        self.audio_queue.put(None)
        self._thread.join(timeout=2)

    def _run(self):
        counter = 0
        threshold = 8

        while not self._stop_event.is_set():
            try:
                chunk = self.audio_queue.get(timeout=0.5)

                if chunk is None:
                    break

                if self.active:
                    audio_data = np.from_buffer(chunk, dtype=np.int16).astype(np.float32) / 32768
                    is_speech = self.vad.process(audio_data)

                    if is_speech:
                        counter = 0
                    else:
                        counter += 1
                        if counter >= threshold:
                            self.on_silence()
                            counter = 0
            except queue.Empty:
                continue
