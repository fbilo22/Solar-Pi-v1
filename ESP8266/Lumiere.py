from machine import Pin, reset

class Lumiere:
    def __init__(self, pin_number):
        self.pin = Pin(pin_number, Pin.OUT )
        self.value( 0 )
        self.last_state = "ARRET"
        self.last_state_time = 0
