# coding: utf8
""" SolarPI - code main.py du ESP8266 v0.1 

	Envoi des données température et contrôle des lumières via  serveur MQTT
 """ 

from machine import Pin, reset
import time
from ubinascii import hexlify
from network import WLAN
import re
from Lumiere import Lumiere


CLIENT_ID = 'ESP8266'

# Utiliser résolution DNS (serveur en ligne) 
# MQTT_SERVER = 'test.mosquitto.org'
#
# Utiliser IP si le Pi en adresse fixe 
# (plus fiable sur réseau local/domestique)
# MQTT_SERVER = '192.168.1.220'
#
# Utiliser le hostname si Pi en DHCP et que la propagation
# du # hostname atteind le modem/router (voir aussi 
# gestion mDns sur router). # (pas forcement fiable sur 
# réseau domestique)
# MQTT_SERVER = 'solarpi'
#
# Attention: MicroPython sous ESP8266 ne gère pas mDns!

MQTT_SERVER = "192.168.4.1"

# Mettre a None si pas utile
MQTT_USER = 'engineer'
MQTT_PSWD = 'domdom2222'

# redemarrage auto après erreur 
ERROR_REBOOT_TIME = 60 # 1 min = 60 sec

#----------------------------------------------
# Lumières 1 à 7

LUM1_PIN = 14   # Broche activation
LUM2_PIN = 12   # Broche activation
LUM3_PIN = 13   # Broche activation
LUM4_PIN = 15   # Broche activation
LUM5_PIN = 0   # Broche activation
LUM6_PIN = 16   # Broche activation
LUM7_PIN = 2    # Broche activation

#-----------------------------------------------
# Power Meters


# --- Demarrage conditionnel ---
runapp = Pin( 12,  Pin.IN, Pin.PULL_UP )
led = Pin( 0, Pin.OUT )
led.value( 1 ) # eteindre

def led_error( step ):
	global led
	t = time.time()
	while ( time.time()-t ) < ERROR_REBOOT_TIME:
		for i in range( 20 ):
			led.value(not(led.value()))
			time.sleep(0.100)
		led.value( 1 ) # eteindre
		time.sleep( 1 )
		# clignote nbr fois
		for i in range( step ):
			led.value( 0 ) 
			time.sleep( 0.5 )
			led.value( 1 )
			time.sleep( 0.5 )
		time.sleep( 1 )
	# Re-start the ESP
	reset()

if runapp.value() != 1:
	from sys import exit
	exit(0)

led.value( 0 ) # allumer

# --- Programme Pincipal ---
def sub_cb( topic, msg ):
	""" fonction de rappel pour souscriptions MQTT """
	# debogage
	#print( '-'*20 )
	#print( topic )
	#print( msg )
	
	# bytes -> str
	t = topic.decode( 'utf8' )
	m = msg.decode('utf8')
	try:
		# if t == "solarpi/lum/1/cmd": 
		if re.match('^solarpi/lum/[0-9]+/cmd$', t): #using regular expression for wildcard
			lum_exec_cmd( cmd = m, topic = t )
	except Exception as e:
		# Capturer TOUTE exception sur souscription
		# Ne pas crasher check_mqtt_sub et 
		#    asyncio.run_until_complete et l'ESP!

		# Info debug sur REPL
		print( "="*20 )
		print( "Subscriber callback (sub_cb) catch an exception:" )
		print( e )
		print( "for topic and message" )
		print( t )
		print( m )
		print( "="*20 )

from umqtt.simple import MQTTClient
try: 
	q = MQTTClient( client_id = CLIENT_ID, 
		server = MQTT_SERVER, 
		user = MQTT_USER, password = MQTT_PSWD )
	q.set_callback( sub_cb )

	if q.connect() != 0:
		led_error( step=1 )
	
	q.subscribe( 'solarpi/lum/#/cmd' )
except Exception as e:
	print( e )
	# check MQTT_SERVER, MQTT_USER, MQTT_PSWD
	led_error( step=2 ) 

# chargement des bibliotheques
try:
	from onewire import OneWire
	from ds18x20 import DS18X20
	from machine import Pin
except Exception as e:
	print( e )
	led_error( step=3 )

# declare le bus i2c (if any)
#
# i2c = I2C( sda=Pin(4), scl=Pin(5) )

# créer les senseurs
try:
	# Senseur temp DS18B20
	#ds = DS18X20( OneWire(Pin(DS18B20_PIN)))
	#roms = ds.scan()
	#if len(roms) == 0:
	#	raise Exception( 'ds18b20 not available!')
	#ds_rom = roms[0]

	# Lumières - init à l'arrêt
	lum1 = Lumiere( LUM1_PIN)
	lum2 = Lumiere( LUM2_PIN)
	lum3 = Lumiere( LUM3_PIN)
	lum4 = Lumiere( LUM4_PIN)
	lum5 = Lumiere( LUM5_PIN)
	lum6 = Lumiere( LUM6_PIN)
	lum7 = Lumiere( LUM7_PIN)

	#Dictionnaires regroupant toutes les lumieres:
	lums = {1:lum1, 2:lum2, 3:lum3, 4:lum4, 5:lum5, 6:lum6, 7:lum7}

except Exception as e:
	print( e )
	led_error( step=4 )

try:
	# annonce connexion objet
	sMac = hexlify( WLAN().config( 'mac' ) ).decode()
	q.publish( "connect/%s" % CLIENT_ID , sMac )
	# Annonce l'état
except Exception as e:
	print( e )
	led_error( step=5 )

import uasyncio as asyncio

def lum_exec_cmd( cmd, topic ):
	""" Executer la commande cmd sur la lumière du topic
	    Modifie l état de la lumière et gère
	    les notification """		
	assert cmd in ("MARCHE","ARRET"), "Invalid lum cmd"

	global q
	global lums

	# TO DO : Extraire le numéro de la lumière dans le topic fourni
	split_topic = topic.split("/") #à valider
	lum_num = int(split_topic[2]) #à valider
	topic_etat = 'solarpi/lum/' + str(lum_num) + '/etat' #à valider
	# Si pas chg d état -> rien faire
	if cmd == lums[lum_num].last_state:
		return 
	# eviter plusieurs chg état en 2 sec
	if (time.time()-lums[lum_num].last_state_time)<2:
		q.publish( topic_etat, "REJECT-CMD" ) # informer du refus
		time.sleep(0.100)
		q.publish( topic_etat, lums[lum_num].last_state ) # Renvoyer l etat 
		return 
	# chg d'état
	lums[lum_num].last_state = cmd
	lums[lum_num].last_state_time = time.time() # en sec
	# changer etat relais
	lums[lum_num].pin.value( 1 if cmd == "MARCHE" else 0 )
	# Notification MQTT du nouvel état
	#   Etat = commande = ("ARRET","ARRET")
	q.publish( topic_etat, cmd ) 

def capture_1h():
	""" Executé pour capturer la temperature chaque heure """
	global ds
	global ds_rom
	# ds18b20 - senseur température 
	ds.convert_temp()
	time.sleep_ms( 750 )
	valeur = ds.read_temp( ds_rom )
	# transformer en chaine de caractères
	t = "{0:.2f}".format(valeur)  
	q.publish( "solarpi/temp", t )

def heartbeat():
	""" Led eteinte 200ms toutes les 10 sec """
	# PS: LED déjà éteinte par run_every!
	time.sleep( 0.2 )

def check_mqtt_sub():
	""" Process the MQTT Subscription messages """
	global q
	# Non-Blocking wait_msg(). Will call mqtt callback  
	# (sub_cb) when a message is received for subscription 
	q.check_msg() # get one message (if any) 

async def run_every( fn, min= 1, sec=None):
	""" Execute a function fn every min minutes 
	    or sec secondes"""
	global led
	wait_sec = sec if sec else min*60
	while True:
		led.value( 1 ) # eteindre pendant envoi/traitement
		try:
			fn()
		except Exception:
			print( "run_every catch exception for %s" % fn)
			raise # quitter loop
		led.value( 0 ) # allumer
		await asyncio.sleep( wait_sec )

async def run_app_exit():
	""" fin d'execution lorsque quitte la fonction """
	global runapp
	while runapp.value()==1:
		await asyncio.sleep( 10 )
	return 

loop = asyncio.get_event_loop()
loop.create_task( run_every(capture_1h    , min=60) ) 
loop.create_task( run_every(heartbeat     , sec=10 ) )
loop.create_task( run_every(check_mqtt_sub, sec=2.5) )
try:
	# Annonce l'etat initial
	for x in range(1,7):
		q.publish( "solarpi/lum/%d/cmd" % (x), last_lum_states[x] )

	# Execution du scheduler
	loop.run_until_complete( run_app_exit() )
except Exception as e :
	print( e )
	led_error( step=6 )

loop.close()
led.value( 1 ) # eteindre 
print( "Fin!")
