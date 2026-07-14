import numpy as np
from threading import Thread
from openwakeword.model import Model

class WakewordModule:
       def __init__(self, audio_queue, trigger_phrase, on_detected):
           self.audio_queue = audio_queue
           self.trigger_phrase = trigger_phrase
           self.on_detected = on_detected
           self.active = True

           self.model = Model(wakeword_models=[f"{trigger_phrase}.tflite"])

           self.thread = Thread(target=self._run, daemon=True)
           self.thread.start()

       def _run(self):
           while True:
               chunk = self.audio_queue.get()
               if chunk is None: break

               if self.active:
                   data = np.frombuffer(chunk, dtype=np.int16)

                   self.model.predict(data)

                   if self.model.predictions[self.trigger_phrase] > 0.5:
                       self.on_detected()


       def set_active(self, is_active):
           self.active = is_active
