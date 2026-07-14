import pyaudio
import queue
import threading

class AudioHandler:
    def __init__(self, rate=16000, chunk=1024):
        self.rate = rate
        self.chunk = chunk
        self.p = pyaudio.PyAudio()
        self._subscribers = []
        self._sub_lock = threading.Lock()
        self.input_queue = queue.Queue(maxsize=100) 
        self.output_queue = queue.Queue()
        self._stop_event = threading.Event()
        self.output_thread = None
        self.input_stream = None

    def subscribe(self) -> queue.Queue:
        new_q = queue.Queue(maxsize=100)
        with self._sub_lock:
            self._subscribers.append(new_q)
        return new_q

    def _input_callback(self, in_data, frame_count, time_info, status):
        with self._sub_lock:
            try:
                self.input_queue.put_nowait(in_data)
            except queue.Full:
                pass
            for q in self._subscribers:
                try:
                    q.put_nowait(in_data)
                except queue.Full:
                    pass
        return (in_data, pyaudio.paContinue)

    def _play_loop(self):
        stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=self.rate, output=True, frames_per_buffer=self.chunk)
        while not self._stop_event.is_set():
            try:
                data = self.output_queue.get(timeout=0.1)
                if data is None: break
                stream.write(data)
                self.output_queue.task_done()
            except queue.Empty:
                continue
        stream.stop_stream()
        stream.close()

    def start(self):
        self.input_stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=self.rate, input=True, frames_per_buffer=self.chunk, stream_callback=self._input_callback)
        self.output_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.output_thread.start()

    def play(self, audio_bytes):
        for i in range(0, len(audio_bytes), self.chunk * 2):
            self.output_queue.put(audio_bytes[i : i + self.chunk * 2])

    def cancel_playback(self):
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
                self.output_queue.task_done()
            except queue.Empty: break

    def stop(self):
        self._stop_event.set()
        self.output_queue.put(None)
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_thread:
            self.output_thread.join()
        self.p.terminate()
