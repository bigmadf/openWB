#!/usr/bin/python3
import sys
import os
import time
import struct
import logging
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.client.sync import ModbusTcpClient
from smarthome.smartlog import initlog
from smarthome.smartret import writeret
named_tuple = time.localtime()  # getstruct_time
devicenumber = int(sys.argv[1])
ipadr = str(sys.argv[2])
uberschuss = int(sys.argv[3])
try:
    navvers = str(sys.argv[4])
except Exception:
    navvers = "2"
initlog("idm", devicenumber)
log = logging.getLogger("idm")
bp = '/var/www/html/openWB/ramdisk/smarthome_device_'
file_stringpv = bp + str(devicenumber) + '_pv'
file_stringcount = bp + str(devicenumber) + '_count'
file_stringcount5 = bp + str(devicenumber) + '_count5'
count5 = 999
if os.path.isfile(file_stringcount5):
    with open(file_stringcount5, 'r') as f:
        count5 = int(f.read())
count5 = count5+1
if count5 > 6:
    count5 = 0
with open(file_stringcount5, 'w') as f:
    f.write(str(count5))
if count5 == 0:
    # pv modus
    pvmodus = 0
    if os.path.isfile(file_stringpv):
        with open(file_stringpv, 'r') as f:
            pvmodus = int(f.read())
    # log counter
    count1 = 999
    if os.path.isfile(file_stringcount):
        with open(file_stringcount, 'r') as f:
            count1 = int(f.read())
    count1 = count1+1
    if count1 > 80:
        count1 = 0
    with open(file_stringcount, 'w') as f:
        f.write(str(count1))
    # aktuelle Leistung lesen
    client = ModbusTcpClient(ipadr, port=502)
    start = 4122
    if navvers == "2":
        rr = client.read_input_registers(start, 2, unit=1)
    else:
        rr = client.read_holding_registers(start, 2, unit=1)
    raw = struct.pack('>HH', rr.getRegister(1), rr.getRegister(0))
    lkw = float(struct.unpack('>f', raw)[0])
    aktpower = int(lkw*1000)
    # logik nur schicken bei pvmodus
    modbuswrite = 0
    if pvmodus == 1:
        modbuswrite = 1
    # Nur positiven Uberschuss schicken, nicht aktuelle Leistung
    neupower = uberschuss
    if neupower < 0:
        neupower = 0
    if neupower > 40000:
        neupower = 40000
    # wurde IDM gerade ausgeschaltet ?    (pvmodus == 99 ?)
    # dann 0 schicken wenn kein pvmodus mehr
    # und pv modus ausschalten
    if pvmodus == 99:
        modbuswrite = 1
        neupower = 0
        pvmodus = 0
        with open(file_stringpv, 'w') as f:
            f.write(str(pvmodus))
    lkwneu = float(neupower)
    lkwneu = lkwneu/1000
    builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                   wordorder=Endian.Little)
    builder.add_32bit_float(lkwneu)
    regnew = builder.to_registers()
    # json return power = aktuelle Leistungsaufnahme in Watt,
    # on = 1 pvmodus, powerc = counter in kwh
    an = '{"power":' + str(aktpower) + ',"powerc":0,"on":' + str(pvmodus) + '}'
    writeret(an, devicenumber)
    if count1 < 3:
        log.info(" %d ipadr %s ueberschuss %6d Akt Leistung %6d"
                 % (devicenumber, ipadr, uberschuss, aktpower))
        log.info(" %d ipadr %s ueberschuss %6d pvmodus %1d modbusw %1d"
                 % (devicenumber, ipadr, neupower, pvmodus, modbuswrite))
    # modbus write
    if modbuswrite == 1:
        client.write_registers(74, regnew, unit=1)
        if count1 < 3:
            log.info("devicenr %d ipadr %s device written by modbus " %
                     (devicenumber, ipadr))
