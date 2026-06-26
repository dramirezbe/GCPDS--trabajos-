

# si realtime = null

Esperar 5 minutos para empezar a adquirir cada acquisition_period_s.

# si realtime tiene algo

No esperar. Comenzar a adquirir inmediatamente a lo que dé el dispositivo. (Hacer GET jobs, ver si realtime es no null, adquirir inmediatamente, mandar POST jobs, todo esto en un superloop, hasta que realtime sea null)