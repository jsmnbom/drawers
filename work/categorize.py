"""Assign categories, descriptions and kinds to dedup3 output.

Each entry gets:
  category            canonical category string
  category_source     label | part_number | context | inferred
                      label       = OCR read a category word on the label
                      part_number = derived from a recognised part number / value
                      context     = only from neighbouring drawers (same pan segment)
                      inferred    = guess from what such drawers/kits usually hold
  category_confidence high | medium | low
  description         short human-readable meaning (part function, Danish -> English)
  kind                drawer | reel | section_label | bin
  note                optional caveat
Writes ../inventory.json ({inventory, review_queue}) and ../inventory.md.
"""
import json, re, collections

# empty when imported (export_verified.py uses describe()); the passes below then do nothing
inv = json.load(open('dedup3_out.json')) if __name__ == '__main__' else []

# ---------------------------------------------------------------- helpers
def K(e):  # normalized key
    return e['part_key']

def kind_of(e):
    if e.get('_column'):
        return 'column_label'
    ws = ' | '.join(e['_wheres']).lower()
    n = len(e['_wheres'])
    reel = sum(1 for w in e['_wheres'] if re.search(r'reel|red tag|red label|orange label', w.lower()))
    if reel >= max(1, n // 2) and 172 < e['t_first'] < 211:
        return 'reel'
    sec = sum(1 for w in e['_wheres'] if re.search(
        r'divider|header|cabinet label|shelf ledge|shelf edge|tape label above|top of (the )?(gray|right|blue|cabinet)|top edge|cabinet section|label above', w.lower()))
    if sec >= max(1, (n + 1) // 2):
        return 'section_label'
    if re.search(r'\bbin\b', ws) and not re.search(r'drawer', ws):
        return 'bin'
    return 'drawer'

E96 = [1.00,1.02,1.05,1.07,1.10,1.13,1.15,1.18,1.21,1.24,1.27,1.30,1.33,1.37,1.40,1.43,1.47,1.50,
       1.54,1.58,1.62,1.65,1.69,1.74,1.78,1.82,1.87,1.91,1.96,2.00,2.05,2.10,2.15,2.21,2.26,2.32,
       2.37,2.43,2.49,2.55,2.61,2.67,2.74,2.80,2.87,2.94,3.01,3.09,3.16,3.24,3.32,3.40,3.48,3.57,
       3.65,3.74,3.83,3.92,4.02,4.12,4.22,4.32,4.42,4.53,4.64,4.75,4.87,4.99,5.11,5.23,5.36,5.49,
       5.62,5.76,5.90,6.04,6.19,6.34,6.49,6.65,6.81,6.98,7.15,7.32,7.50,7.68,7.87,8.06,8.25,8.45,
       8.66,8.87,9.09,9.31,9.53,9.76]
E24 = [1.0,1.1,1.2,1.3,1.5,1.6,1.8,2.0,2.2,2.4,2.7,3.0,3.3,3.6,3.9,4.3,4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1]

def parse_r(s):
    """'4.75KΩ' -> ohms float, or None."""
    m = re.fullmatch(r'(\d+(?:[.,]\d+)?)(R|K|M)?Ω?', s.upper())
    if not m:
        return None
    v = float(m.group(1).replace(',', '.'))
    return v * {None: 1, 'R': 1, 'K': 1e3, 'M': 1e6}[m.group(2)]

def in_series(v, series):
    if v == 0:
        return True
    import math
    mant = v / 10 ** math.floor(math.log10(v))
    return any(abs(mant - s) < 0.006 * s for s in series)

def fmt_r(v):
    if v >= 1e6: return f'{v/1e6:g} MΩ'
    if v >= 1e3: return f'{v/1e3:g} kΩ'
    return f'{v:g} Ω'

# ---------------------------------------------------------------- 74 / 4000 function tables
F74 = {'00':'quad NAND','01':'quad NAND OC','02':'quad NOR','03':'quad NAND OC','04':'hex inverter',
 '05':'hex inverter OC','06':'hex inverter buffer OC','07':'hex buffer OC','08':'quad AND','09':'quad AND OC',
 '10':'triple 3-in NAND','11':'triple 3-in AND','12':'triple 3-in NAND OC','13':'dual Schmitt NAND',
 '14':'hex Schmitt inverter','15':'triple AND OC','20':'dual 4-in NAND','21':'dual 4-in AND','27':'triple NOR',
 '30':'8-in NAND','32':'quad OR','37':'quad NAND buffer','38':'quad NAND buffer OC','42':'BCD-decimal decoder',
 '47':'BCD-7seg decoder/driver','48':'BCD-7seg decoder','51':'AND-OR-invert','54':'AND-OR-invert','73':'dual JK FF',
 '74':'dual D FF','75':'quad latch','76':'dual JK FF','83':'4-bit adder','85':'4-bit comparator','86':'quad XOR',
 '90':'decade counter','92':'divide-by-12 counter','93':'4-bit binary counter','95':'4-bit shift register',
 '107':'dual JK FF','109':'dual JK FF','112':'dual JK FF','121':'monostable','122':'retriggerable monostable',
 '123':'dual monostable','125':'quad 3-state buffer','126':'quad 3-state buffer','132':'quad Schmitt NAND',
 '133':'13-in NAND','136':'quad XOR OC','137':'3-to-8 decoder w/ latch','138':'3-to-8 decoder','139':'dual 2-to-4 decoder',
 '145':'BCD-decimal decoder/driver','147':'10-to-4 priority encoder','148':'8-to-3 priority encoder','150':'16:1 mux',
 '151':'8:1 mux','153':'dual 4:1 mux','154':'4-to-16 decoder','155':'dual 2-to-4 decoder','156':'dual 2-to-4 decoder OC',
 '157':'quad 2:1 mux','158':'quad 2:1 mux inv','160':'decade counter','161':'4-bit binary counter','162':'decade counter',
 '163':'4-bit binary counter','164':'8-bit SIPO shift reg','165':'8-bit PISO shift reg','166':'8-bit shift reg',
 '170':'4x4 register file','173':'quad D reg 3-state','174':'hex D FF','175':'quad D FF','181':'4-bit ALU',
 '182':'look-ahead carry','189':'64-bit RAM','190':'up/down decade counter','191':'up/down binary counter',
 '192':'up/down decade counter','193':'up/down binary counter','194':'4-bit universal shift reg','195':'4-bit shift reg',
 '196':'presettable decade counter','197':'presettable binary counter','198':'8-bit shift reg','199':'8-bit shift reg',
 '221':'dual monostable','237':'3-to-8 decoder w/ latch','238':'3-to-8 decoder','240':'octal inverting buffer',
 '241':'octal buffer','242':'quad transceiver inv','243':'quad transceiver','244':'octal buffer','245':'octal transceiver',
 '247':'BCD-7seg decoder','248':'BCD-7seg decoder','251':'8:1 mux 3-state','253':'dual 4:1 mux 3-state',
 '257':'quad 2:1 mux 3-state','258':'quad 2:1 mux 3-state inv','259':'8-bit addressable latch','260':'dual 5-in NOR',
 '266':'quad XNOR OC','273':'octal D FF','280':'parity generator','283':'4-bit adder','288':'32x8 PROM',
 '292':'programmable divider','298':'quad 2-in mux w/ storage','299':'8-bit universal shift reg','323':'8-bit shift reg',
 '352':'dual 4:1 mux inv','353':'dual 4:1 mux inv 3-state','365':'hex buffer 3-state','366':'hex inverter 3-state',
 '367':'hex buffer 3-state','368':'hex inverter 3-state','373':'octal latch','374':'octal D FF','375':'quad latch',
 '377':'octal D FF w/ enable','390':'dual decade counter','393':'dual 4-bit counter','395':'4-bit shift reg 3-state',
 '540':'octal inverting buffer','541':'octal buffer','573':'octal latch','574':'octal D FF','590':'8-bit counter w/ reg',
 '595':'8-bit shift reg w/ latch','597':'8-bit shift reg','624':'VCO','629':'dual VCO','640':'octal transceiver inv',
 '645':'octal transceiver','670':'4x4 register file','682':'8-bit comparator','688':'8-bit comparator',
 '4040':'12-stage counter','4060':'14-stage counter/osc','4511':'BCD-7seg driver','922':'16-key encoder','923':'20-key encoder'}

F4000 = {'4001':'quad NOR','4002':'dual 4-in NOR','4006':'18-stage shift reg','4007':'dual complementary pair',
 '4008':'4-bit adder','4009':'hex inverting buffer','4010':'hex buffer','4011':'quad NAND','4012':'dual 4-in NAND',
 '4013':'dual D FF','4014':'8-stage shift reg','4015':'dual 4-stage shift reg','4016':'quad bilateral switch',
 '4017':'decade counter/divider','4018':'presettable divide-by-N','4019':'quad AND/OR select','4020':'14-stage counter',
 '4021':'8-stage shift reg','4022':'octal counter/divider','4023':'triple 3-in NAND','4024':'7-stage counter',
 '4025':'triple 3-in NOR','4026':'decade counter 7-seg out','4027':'dual JK FF','4028':'BCD-decimal decoder',
 '4029':'presettable up/down counter','4030':'quad XOR','4035':'4-bit shift reg','4040':'12-stage counter',
 '4042':'quad D latch','4043':'quad NOR RS latch','4044':'quad NAND RS latch','4046':'PLL','4047':'mono/astable multivibrator',
 '4049':'hex inverting buffer','4050':'hex buffer','4051':'8-ch analog mux','4052':'dual 4-ch analog mux',
 '4053':'triple 2-ch analog mux','4060':'14-stage counter/oscillator','4063':'4-bit magnitude comparator',
 '4066':'quad bilateral switch','4067':'16-ch analog mux','4068':'8-in NAND','4069':'hex inverter','4070':'quad XOR',
 '4071':'quad OR','4072':'dual 4-in OR','4073':'triple 3-in AND','4075':'triple 3-in OR','4076':'quad D register 3-state',
 '4077':'quad XNOR','4078':'8-in NOR','4081':'quad AND','4082':'dual 4-in AND','4085':'dual AND-OR-invert',
 '4093':'quad Schmitt NAND','4094':'8-stage shift/store reg','4098':'dual monostable','4099':'8-bit addressable latch',
 '40106':'hex Schmitt inverter','4502':'strobed hex inverter','4503':'hex 3-state buffer','4510':'BCD up/down counter',
 '4511':'BCD-7seg latch/driver','4512':'8-ch data selector','4514':'4-to-16 decoder/latch','4515':'4-to-16 decoder/latch inv',
 '4516':'binary up/down counter','4518':'dual BCD counter','4520':'dual binary counter','4521':'24-stage divider',
 '4526':'programmable 4-bit down counter','4528':'dual monostable','4532':'8-bit priority encoder','4538':'dual precision monostable',
 '4541':'programmable timer','4543':'BCD-7seg latch/driver','4553':'3-digit BCD counter','4555':'dual 1-of-4 decoder',
 '4556':'dual 1-of-4 decoder inv','4584':'hex Schmitt trigger'}

def desc74(key):
    nums = re.findall(r'(?:74X?|X|4X)\s*(\d{2,4})', key)
    nums = nums or re.findall(r'\d{2,4}', key)
    parts = []
    for n in nums:
        f = F74.get(n)
        parts.append(f'74x{n}' + (f' {f}' if f else ''))
    return '; '.join(parts) if parts else None

def desc4000(key):
    nums = re.findall(r'4\d{3,4}', key)
    parts = []
    for n in nums:
        f = F4000.get(n)
        parts.append(f'CD{n}' + (f' {f}' if f else ''))
    return '; '.join(parts) if parts else None

# ---------------------------------------------------------------- part-number rules
# (regex on normalized key, category, confidence, description)
# Regexes are matched with re.search on the '/'-joined normalized key.
RULES = [
 # --- Danish section words / hardware ------------------------------------
 (r'^TRACISPACE', 'Transistor mounting hardware', 'medium', 'Danish: "div. transistor mont. tilbehør" = assorted transistor mounting accessories (insulators, bushings, clips)'),
 (r'^KLEMMUFFER$', 'Cable/hose clamp sleeve', 'low', 'Danish "klemmuffe" = clamp sleeve / compression coupling'),
 (r'^DCMOTOR$', 'Motor', 'high', 'Small DC motors'),
 (r'^SOLENOID/VALVES$', 'Solenoid valve', 'high', 'Solenoid valves'),
 (r'^(BATTERYHOLDER|BATTERIHOLDER)', 'Battery holder', 'high', None),
 (r'^GLØDEPÆRER$', 'Lamp (incandescent)', 'high', 'Danish "glødepærer" = incandescent bulbs'),
 (r'^DIODER$', 'Diode', 'high', 'Danish "dioder" = diodes (cabinet header)'),
 (r'^(EFFEKTMODS?|EFFEKTMODSTANDE)$', 'Resistor (power)', 'high', 'Danish "effektmodstande" = power resistors (cabinet label)'),
 (r'^(MODSTANDE|OSTANDE|TANDE|STANDE)$', 'Resistor', 'high', 'Danish "modstande" = resistors (cabinet/divider label, partly cut off)'),
 (r'KONDENSAT', 'Capacitor', 'high', 'Danish "kondensatorer" = capacitors'),
 (r'^SPOLER?/', 'Inductor', 'high', 'Danish "spole(r)" = coil(s); values in µH, 1S82/xx look like Philips/Vogt choke part codes'),
 (r'^SOK+EL/|^SOCKEL', 'IC socket', 'high', 'Danish "sokkel" = IC socket; pin count on label'),
 (r'^JUMPERS', 'Jumper', 'high', '2.54 mm shorting jumpers'),
 (r'^TNUT|^T-NUT|^1-NUT$', 'T-nut', 'high', 'T-slot nuts (OCR "1-nut" = t-nut)'),
 (r'VINGEM', 'Wing nut', 'high', 'Danish "vingemøtrik" = wing nut'),
 (r'HÆTTEM|HAETTEM', 'Cap nut', 'high', 'Danish "hættemøtrik" = cap (acorn) nut'),
 (r'INDSLAGSM', 'Insert nut', 'high', 'Danish "indslagsmøtrik" = hammer-in / pronged tee nut'),
 (r'MØTRIK|MOTRIK', 'Nut', 'high', 'Danish "møtrik(ker)" = nut(s); "usorterede" = unsorted'),
 (r'^FIRKANTEDE$', 'Nut (square)', 'medium', 'Danish "firkantede" = square (nuts), in nut section'),
 (r'^(EKSTRA)?FLADE$', 'Nut (thin/flat)', 'medium', 'Danish "flade"/"ekstra flade" = flat / extra-thin nuts, in nut section'),
 (r'FJEDERSKIVE', 'Spring washer', 'high', 'Danish "fjederskive" = spring (lock) washer'),
 (r'TALLERKENSKIVE', 'Disc spring', 'high', 'Danish "tallerkenskive" = Belleville / disc spring washer'),
 (r'GUMMISKIVER', 'Rubber washer', 'high', 'Danish "gummiskiver" = rubber washers'),
 (r'SKÆRESKIVER|SKAERESKIVER', 'Cutting disc', 'medium', 'Danish "skæreskiver" = cutting discs (M5 arbor)'),
 (r'M\.?SKIVER?$', 'Screw/bolt (with washer)', 'high', 'Danish "m. skive" = with washer (flanged / sems screw)'),
 (r'SKIVER$', 'Washer', 'high', 'Danish "skiver" = washers'),
 (r'^\d+\.\d+(MM|X\d+)$', 'Washer', 'medium', 'Washer size (hole diameter x outer diameter), in washer section'),
 (r'^FJEDRE$', 'Spring', 'high', 'Danish "fjedre" = springs'),
 (r'^STAG$', 'Standoff/strut', 'low', 'Danish "stag" = stays/struts; in hardware cabinet, likely standoffs or rods'),
 (r'^GEVINDST', 'Threaded rod', 'high', 'Danish "gevindstænger" = threaded rods'),
 (r'^GEVINDNITTER', 'Rivet nut', 'high', 'Danish "gevindnitter" = rivet nuts'),
 (r'^GEVINDINDSATSER', 'Thread insert', 'high', 'Danish "gevindindsatser" = threaded inserts (Helicoil-type)'),
 (r'^PASBOLTE', 'Shoulder bolt', 'high', 'Danish "pasbolte" = shoulder / fitted bolts'),
 (r'^LINKSGEVIND', 'Screw/bolt (left-hand)', 'high', 'Danish "linksgevind" = left-hand thread'),
 (r'PINOLBOR', 'Drill bit (centre)', 'high', 'Danish "pinolbor" = centre drill'),
 (r'^PINOL', 'Set screw', 'high', 'Danish "pinolskrue" = set (grub) screw'),
 (r'^INOL', 'Set screw', 'medium', 'Cut-off "PINOL M8x25" = set screw'),
 (r'^TRAEBOR|^TRÆBOR', 'Drill bit (wood)', 'high', 'Danish "træbor" = wood drill bits'),
 (r'^MURBOR', 'Drill bit (masonry)', 'high', 'Danish "murbor" = masonry drill bits'),
 (r'SELVCENTRERENDE', 'Drill bit (self-centering)', 'high', 'Danish "selvcentrerende bor" = self-centering (hinge) drill bits'),
 (r'^HSS', 'Drill bit', 'high', 'HSS twist drill bits, size on label; "blandet" = mixed'),
 (r'^\d+(\.\d+)?MM$', 'Drill bit', 'medium', 'Size only; in drill-bit section'),
 (r'^M\d+(\.\d+)?X\d+', 'Screw/bolt', 'high', 'Metric screw, size x length; 6K = hex head, A2 = stainless, allen = socket head'),
 (r'^\d+X\d+TX\d+', 'Screw/bolt', 'high', 'Torx (TX) screw, A2 stainless'),
 (r'^M\d+(\.\d+)?(,M\d+(\.\d+)?)+$', 'Screw/bolt', 'medium', 'Small metric screws (sizes listed)'),
 (r'(^|/)(M\d+|\d+X)?/?ALLEN|ALLEN', 'Screw/bolt (socket head)', 'high', 'Allen / socket-head cap screws'),
 (r'USAE|USÆ|U\.?SAENK|U\.?SÆNK', 'Screw/bolt (countersunk)', 'high', 'Danish "undersænket" = countersunk'),
 (r'LÅS|LAS$', 'Lock nut', 'high', 'Danish "låsemøtrik" = lock (nyloc) nut'),
 (r'FLANGE', 'Screw/bolt (flanged)', 'high', None),
 (r'MESSING', 'Screw/bolt (brass)', 'high', 'Danish "messing" = brass'),
 (r'^M\d+/?6K|6K/?M\d+|6KBLANDET|^M\d+6K', 'Screw/bolt (hex head)', 'high', 'Danish "6K" (sekskant) = hex head; "blandet" = mixed'),
 (r'(?<!U)SORTE?$', 'Screw/bolt (black)', 'high', 'Danish "sorte" = black (oxide) finish'),
 (r'USORT|BLANDET', 'Fastener (unsorted)', 'medium', 'Danish "usorteret"/"blandet" = unsorted / mixed; "halvsmå" = smallish, "meget små" = very small'),
 (r'^\d+XM\d+$', 'Screw/bolt', 'medium', 'e.g. 6x M8'),
 (r'^M\d+$', 'Screw/bolt', 'medium', 'Metric size only; in the screw cabinet'),

 # --- electromechanical ----------------------------------------------------
 (r'REEDRELAY', 'Reed relay', 'high', '5 V reed relay'),
 (r'RELAY', 'Relay', 'high', 'Coil voltage on label; 6.000.xxxx looks like a supplier stock number'),
 (r'^SWITCH/SPST/DIL', 'Switch', 'high', 'DIL (DIP) switch, SPST'),
 (r'^BRIDGE/RECTIFIERS', 'Bridge rectifier', 'high', None),
 (r'^(RED|GREEN|YELLOW)?LED$', 'LED', 'high', None),
 (r'^7-SEG', 'Display (7-segment)', 'high', None),
 (r'^BPW34', 'Photodiode', 'high', 'BPW34 PIN photodiode'),
 (r'^\d+(\.\d+)?MHZ|^KDS8C/|KHZ$', 'Crystal', 'high', 'Quartz crystals; KDS 32.768 kHz is a watch crystal'),

 # --- passives -------------------------------------------------------------
 (r'MULTITU', 'Trim pot (multiturn)', 'high', 'Multiturn trimmer potentiometer'),
 (r'TRIMPOT', 'Trim pot', 'high', 'Single-turn trimmer potentiometer'),
 (r'RESNETWORK', 'Resistor network', 'high', 'Bourns 4608X-type resistor network'),
 (r'^SMD-?0?6?0?3?$|^MD-0603$|^SMD-0$', 'Resistor (SMD 0603)', 'medium', 'SMD 0603 section label (shelf of reels)'),
 (r'^0603/', 'Resistor (SMD 0603)', 'high', None),
 (r'^[\d.,]+Ω.*/POWER$', 'Resistor (power)', 'high', 'Power (wirewound/cement) resistor; label lists the values'),
 (r'^POWER$', 'Resistor (power)', 'high', None),

 # --- diodes ---------------------------------------------------------------
 (r'/SCHOTTKY', 'Diode (Schottky)', 'high', None),
 (r'/TVS', 'Diode (TVS)', 'high', 'BZW04 transient voltage suppressor'),
 (r'ZENER|^ZD\d+|^BZX|^1N7\d\dA|^1N9\d\dB|^\d{3}B/\d{3}B', 'Diode (zener)', 'high', None),
 (r'^X55C12', 'Diode (zener)', 'high', 'BZX55C12 (cut off)'),
 (r'^1N4148', 'Diode (signal)', 'high', '1N4148 small-signal diode'),
 (r'/SIGNAL$|^AAZ1\d', 'Diode (signal)', 'high', 'AAZ18 germanium signal diode'),
 (r'^1N4\d{3}|^1N5\d{3}|^RHC\d|^BY\d{3}|^RGP10|^N4942|^1N6\d{3}', 'Diode (rectifier)', 'high', None),
 (r'/DIODE$', 'Diode', 'high', None),

 # --- transistors ----------------------------------------------------------
 (r'IGBT', 'IGBT', 'high', 'GBC40F-type IGBT'),
 (r'JFETN-CH|^U1899', 'JFET', 'high', 'U1899E N-channel JFET'),
 (r'DARLINGTONARRAY|SEVEN/DARLINGTON|^ULN2\d{3}|^L201/', 'Darlington array', 'high', 'ULN2003/2004/2803/2804/2823-type 7/8-channel Darlington driver arrays'),
 (r'DARLINGTON', 'Transistor (Darlington)', 'high', 'TIP127 PNP Darlington'),
 (r'/P-CH', 'MOSFET (P-ch)', 'high', None),
 (r'/N-CH', 'MOSFET (N-ch)', 'high', None),
 (r'^IRF|^BUK|^RFP', 'MOSFET', 'high', None),
 (r'/PNP|^557B', 'Transistor (PNP)', 'high', None),
 (r'/NPN', 'Transistor (NPN)', 'high', None),
 (r'^BC(107|182|337|547|639|301)', 'Transistor (NPN)', 'high', 'Small-signal NPN'),
 (r'^BC(327|557|640)|^BD(234|950)|^BFT80|^MJE15031', 'Transistor (PNP)', 'high', None),
 (r'^BD(138|738)', 'Transistor (PNP)', 'medium', 'BD138 medium-power PNP (BD738 is probably a misread of BD138)'),
 (r'^BUJ|^BU508|^BUT90|^MJE3055|^2N3055|^2N6292|^BDY1|^MJ3001|^BD413|^2N3738', 'Transistor (NPN)', 'high', 'Power NPN'),
 (r'TRANSISTOR$', 'Transistor', 'high', None),

 # --- optos ----------------------------------------------------------------
 (r'OPTOCOUPLER|^6N13[679]|^TIL111|^PC817|^CNY|^MOC30|^MCP30|^ILQ|^TCDT|^H11A', 'Optocoupler', 'high', 'MOC/MCP3010/3063 are triac-output optocouplers; 6N137/6N136/6N139 high-speed'),

 # --- memory / processors ---------------------------------------------------
 (r'EEPROM|^24C\d+|^93C\d+|^HN58', 'Memory (EEPROM)', 'high', None),
 (r'EP?ROM|ERROM|^27\d{2,3}|^2516|^2732|^2764', 'Memory (EPROM)', 'high', 'UV-erasable EPROM (2716=2 KB … 27512=64 KB); suffix -20/-25/-30/-45 = access time in 10 ns'),
 (r'BI-POLAR/PROM|^TBP18S030|PROGRAMMABLE/READ-ONLY', 'Memory (PROM)', 'high', '32x8 bipolar fusible-link PROM'),
 (r'DRAM|^KM4164|^TMS4256|^MM5290|^UPD41?16|^V53C256|^MB81C4256', 'Memory (DRAM)', 'high', None),
 (r'SRAM|^93L415|^MN2114|^M5M5165|^DS1225', 'Memory (SRAM)', 'high', 'DS1225Y is battery-backed NVRAM'),
 (r'/RAM$|^XX6116|^AM29700', 'Memory (SRAM)', 'high', '6116/6264 are 2K/8K x8 SRAM; AM29700 is a 16x4 register-file RAM'),
 (r'^INTEL8080|^ZILOG/Z80|/CPU$|TMS9995|TM69995', 'CPU', 'high', '8-bit microprocessor'),
 (r'^M80C154|MICROCONTROLLER|MCU$', 'Microcontroller', 'high', '80C154 = 8051-family MCU'),
 (r'^D8749', 'Microcontroller', 'high', '8749 = MCS-48 family MCU with EPROM (label says CPU)'),
 (r'^M5L8251|^D8251|USART', 'Peripheral IC (USART)', 'high', '8251 programmable USART'),
 (r'^M5L8253', 'Peripheral IC (timer)', 'high', '8253 programmable interval timer'),
 (r'^TMS9901', 'Peripheral IC', 'high', 'TMS9901 programmable systems interface (I/O + timer)'),
 (r'^CDP6402', 'Peripheral IC (UART)', 'high', 'CDP6402 CMOS UART'),
 (r'^MM58274|^MSM58321|^RTC$', 'RTC', 'high', 'Real-time clock IC'),
 (r'^ISD1016', 'Voice record/playback IC', 'high', 'ISD1016 16 s analog voice recorder'),

 # --- logic ----------------------------------------------------------------
 (r'^10124N|^MC1010[0-9]|^MC1011[0-9]|TTL-ECL', 'Logic (ECL)', 'high', 'Motorola MECL 10K series'),
 (r'^74X|^X\d{2,3}/X|^4X\d{2,3}|^\d{2}/\d{2}(/\d{2})?$|^\d{3}/\d{3}/\d{3}$', 'Logic (74-series)', 'high', None),
 (r'^HC\d{2,3}', 'Logic (74HC)', 'high', None),
 (r'^74LS|^80C95|^81LS9', 'Logic (74-series)', 'high', '80C95 = CMOS hex 3-state buffer; 81LS95/97 = octal 3-state buffers'),
 (r'^40HC-XX', 'Logic (74HC / 40HC)', 'high', 'Mixed 74HC / 40HC (HC-series CMOS 4000) parts'),
 (r'^CD4\d{3,4}|^MC1407\d|^MAA40', 'Logic (CMOS 4000)', 'high', None),
 (r'^40[0-9]{2}$|^45\d\d$', 'Logic (CMOS 4000)', 'high', None),
 (r'NORGATE|/NORGATE', 'Logic (ECL)', 'high', None),

 # --- analog ICs -----------------------------------------------------------
 (r'OPAMP|OPA$|^TL08[124]|^TL081|^LM35[368]|^LF35[36]|^LM324|^LM308|^LM208|^CA3140|^TAA7[68]', 'Op amp', 'high', None),
 (r'COMPARATOR|^LM339|^LM311|^LM219|AM6688', 'Comparator', 'high', None),
 (r'^TL431|SHUNT/REGULATOR', 'Voltage reference (shunt)', 'high', 'TL431 adjustable shunt regulator / reference'),
 (r'^LM336', 'Voltage reference', 'high', 'LM336 2.5 V / 5 V reference'),
 (r'^ICL7660|^7660|NEGATIVE/VOLTAGE/CONVERTER', 'Voltage converter', 'high', 'ICL7660 switched-capacitor voltage inverter'),
 (r'^L4960|SWVREG|^UA78S40|SWREG', 'Voltage regulator (switching)', 'high', 'L4960 2.5 A step-down; µA78S40 universal switching regulator subsystem'),
 (r'NEGATIVE/?VOLTAGE|^79\d\d|^UA79|^LM320|^LM337|^LM104|^79M', 'Voltage regulator (negative)', 'high', '79xx / LM320 / LM337 negative regulators'),
 (r'VOLTAGE/?REGULATOR|VOLTAGE/STABILIZER|^7805|^805$|^LM317|^LM340|^UA78|^78\d\d|^LT1086|^LM723|^TAA550', 'Voltage regulator', 'high', None),
 (r'^NE555|^LM555|^LM556|/TIMER$', 'Timer', 'high', '555 / 556 timers'),
 (r'TONE/DECODER|^XR2211|^LM567', 'Tone decoder / PLL', 'high', 'XR2211 FSK demodulator/tone decoder; LM567 tone decoder'),
 (r'^XR2206', 'Function generator IC', 'high', 'XR2206 monolithic function generator'),
 (r'^LM2917', 'Frequency-to-voltage converter', 'high', 'LM2917 F/V converter (tachometer)'),
 (r'^MT8870', 'Telecom IC (DTMF)', 'high', 'MT8870 DTMF receiver/decoder'),
 (r'^MK5380', 'Telecom IC (dialer)', 'high', 'MK5380 pulse/tone dialer'),
 (r'^AM791[01]', 'Telecom IC (modem)', 'high', 'AM7910/7911 FSK modem'),
 (r'^NE552[01]', 'Analog IC (LVDT)', 'high', 'NE5520/5521 LVDT signal conditioner'),
 (r'^AD7506', 'Analog switch/mux', 'high', 'AD7506 16-channel analog multiplexer'),
 (r'^TSC7107', 'ADC', 'high', 'ICL7107 3½-digit ADC with LED driver'),
 (r'^SL6270', 'Audio IC', 'high', 'SL6270 AGC microphone amplifier'),
 (r'^MC3361', 'RF IC', 'high', 'MC3361 narrowband FM IF'),
 (r'^SL611C|RF/IF', 'RF IC', 'high', 'SL611 RF/IF amplifier'),
 (r'^SL521C|LOG/AMPLIFIER', 'RF IC', 'high', 'SL521 wideband log amplifier'),
 (r'^LM733', 'Amplifier (differential)', 'high', 'LM733 video/differential amplifier'),
 (r'^EL2003', 'Amplifier (video)', 'high', 'EL2003 video line driver'),
 (r'^LH0033|^LH0002|/BUFFER$', 'Buffer amplifier', 'high', 'LH0002/LH0033 high-speed buffers'),
 (r'^TDA4718|^TEA1507|^NCP1200', 'Power management IC (SMPS)', 'high', 'SMPS / PWM controllers'),
 (r'^MAYBE|MAX6383|RESET', 'Supervisor / reset IC', 'high', 'MAX638x µP reset circuit (MAX6383XR16D3 = SC70 reset IC, 1.58 V threshold)'),
 (r'^SN7549|^DS7549|MOS-TO-LED', 'Display driver', 'high', 'SN75491/DS75492 MOS-to-LED segment/digit drivers'),
 (r'LINE|^SN75|^SN55|^DS26C31|^LTC485|^MC1488|^MC1489|^MC3441|^751\d\d|TRANSC', 'Line driver/receiver', 'high', None),
 (r'^SAA5|TELETEXT', 'TV IC (teletext)', 'high', 'Philips SAA50xx/52xx teletext decoder chips'),
 (r'TV/CRT|^SAA12|^SPU2|^VCU2|^SL1430', 'TV/video IC', 'high', None),
 (r'^TDA(10|15|20|21|25|27|29|30|33|35|36|37|39|44|45)', 'TV/audio IC (TDA)', 'medium', 'Philips/SGS TDA linear ICs (audio amps, TV IF/deflection/colour decoders)'),
 (r'^TDA', 'TV/audio IC (TDA)', 'medium', None),

 # --- caps / resistors by value --------------------------------------------
 (r'(PF|NF)', 'Capacitor (film/ceramic)', 'high', None),
 (r'(UF|ΜF|µF)', 'Capacitor (electrolytic)', 'medium', None),
 (r'^10\.000$', 'Capacitor (electrolytic)', 'medium', '10.000 µF (Danish thousands separator), value only'),
]
RULES = [(re.compile(rx), c, cf, d) for rx, c, cf, d in RULES]

RVAL = re.compile(r'^(\d+(?:[.,]\d+)?)(R|K|M)?Ω?$')

def classify(e):
    k = K(e)
    lines = e['lines']
    # resistor drawers: every line a value, or values + POWER
    vals = [parse_r(l.replace(' ', '')) for l in k.split('/') if RVAL.fullmatch(l)]
    for rx, cat, conf, desc in RULES:
        if rx.search(k):
            return cat, conf, desc
    if vals and all(RVAL.fullmatch(l) for l in k.split('/')):
        # bare integers without a unit are ambiguous (74HC numbers, washer sizes) -> handled later
        if all(v is not None for v in vals) and not all(re.fullmatch(r'\d+(\.\d+)?', l) for l in k.split('/')):
            return 'Resistor', 'high', 'Through-hole resistor(s): ' + ', '.join(fmt_r(v) for v in vals)
    if re.fullmatch(r'\d{3}', k) and 312 <= e['t_first'] <= 315:
        return 'Resistor', 'high', 'Through-hole resistor ' + fmt_r(float(k)) + ' (tan cabinet, values without unit)'
    return None, None, None

out = []
for e in inv:
    cat, conf, desc = classify(e)
    src = 'part_number' if cat else None
    lab = e.get('label_category')
    if cat and lab and lab.lower().split()[0] in cat.lower():
        src = 'label'
    if not cat and lab:
        cat, conf, src = lab.strip().title(), 'medium', 'label'
    e['category'], e['category_confidence'], e['category_source'], e['description'] = cat, conf, src, desc
    e['kind'] = kind_of(e)
    out.append(e)

# ---------------------------------------------------------------- context pass
WIN = 6.0
for i, e in enumerate(out):
    if e['category']:
        continue
    neigh = collections.Counter()
    for f in out:
        if f is e or not f['category'] or f['category_source'] == 'context':
            continue
        if abs(f['t_first'] - e['t_first']) <= WIN:
            neigh[f['category']] += f['reads_total']
    if neigh:
        cat, n = neigh.most_common(1)[0]
        tot = sum(neigh.values())
        if n / tot >= 0.5:
            e['category'] = cat
            e['category_source'] = 'context'
            e['category_confidence'] = 'low'
            e['description'] = f'No recognisable part on label; neighbouring drawers ({n}/{tot} reads) are {cat}'

# ---------------------------------------------------------------- manual overrides / inferred
OVR = {
 '4071': ('Logic (CMOS 4000)', 'low', 'inferred', 'Blue tape label on top of the resistor cabinet; "4071" could be CD4071 quad OR but is out of place here'),
 '74LS05': ('Logic (74-series)', 'high', 'part_number', '74LS05 hex inverter (OC); cardboard tab in the capacitor cabinet'),
 '60001596': ('Unknown', 'low', 'inferred', 'Looks like a supplier stock number (6000xxxx pattern also seen on relay and BD138 labels), not a part number'),
 'PICO-10.5K125M6A': ('Fuse', 'low', 'inferred', 'Reads like a Littelfuse PICO fuse rating (125 mA?); uncertain'),
 'MPID1603/470G': ('Unknown', 'low', 'inferred', 'Unrecognised code; ".470g" may be a weight'),
 'ML1008': ('Unknown', 'low', 'inferred', 'Unrecognised; sits among bulbs/zeners/fuses'),
 '7ED6/10148/8A': ('Fuse', 'low', 'inferred', '"8A" rating with a stock number; probably fuses (next to bulbs)'),
 '7638/10148/8A': ('Fuse', 'low', 'inferred', '"8A" rating with a stock number; probably fuses (next to bulbs)'),
 'SPC/3624RC/25B': ('Unknown', 'low', 'inferred', 'Unrecognised code'),
 'MOB': ('Unknown', 'low', 'inferred', 'Cut-off handwritten label on top of the fastener cabinet'),
 '?': ('Fastener (unsorted)', 'low', 'context', 'Label unreadable; drawer sits in the nut section'),
 'MESSING': ('Screw/bolt (brass)', 'medium', 'part_number', 'Danish "messing" = brass; size cut off'),
 'USORT': ('Fastener (unsorted)', 'medium', 'part_number', 'Cut off, likely "M3 USORT."'),
 'BLANDET': ('Drill bit', 'medium', 'label', 'Danish "blandet" = mixed; OCR saw a drill-bit label, sits between the HSS and screw drawers'),
 'MEGETSMÅ': ('Fastener (unsorted)', 'medium', 'part_number', 'Danish "meget små" = very small (screws/nuts)'),
 'M6/ALLENPAN': ('Screw/bolt (socket head)', 'medium', 'part_number', 'M6 allen pan-head'),
 'ALLENPAN': ('Screw/bolt (socket head)', 'medium', 'part_number', 'Allen pan-head screws'),
 '1PCTKONDENSAT': ('Capacitor', 'medium', 'part_number', 'Faded handwritten "1% kondensator" = 1 % tolerance capacitors'),
 'VOLTAGE/REGULATOR': ('Voltage regulator', 'high', 'label', 'Part number cut off'),
 '196/TM69995': ('Logic (74HC)', 'medium', 'part_number', 'HC196 counter; "TMS 9995" (16-bit CPU) written over the printed label'),
 '40HC-XX&74HC-XX': ('Logic (74HC / 40HC)', 'high', 'part_number', 'Handwritten card: mixed 40HC and 74HC parts'),
 'M6': None,  # handled below (time-dependent)
 '0.0Ω': ('Resistor (SMD 0603)', 'medium', 'inferred', '0 Ω jumper reel at the left end of the 0603 reel shelf'),
 'LM353': ('Op amp', 'medium', 'inferred', 'Probably LF353 dual JFET op amp (misread) — an "LM353" does not exist'),
 'MAA4001/MAA4004/MAA4051': ('Logic (CMOS 4000)', 'low', 'inferred', 'Tesla (CZ) MAA-prefixed numbers matching 4001/4051; not a standard series, unverified'),
 'MC14/OPA': ('Op amp', 'medium', 'part_number', 'Cut-off "MC14xx OP AMP" (MC1439 drawer next to it)'),
 '6N136/6N139': ('Optocoupler', 'high', 'part_number', '6N136/6N139 high-speed optocouplers'),
 '75188/75188': ('Line driver/receiver', 'high', 'part_number', 'SN75188 quad RS-232 line driver'),
 'LM336': ('Voltage reference', 'high', 'part_number', 'LM336 2.5 V / 5 V shunt reference'),
 'LM356': ('Op amp', 'medium', 'inferred', 'LM356 is not a standard part; probably LF356 JFET op amp'),
 'BC182': ('Transistor (NPN)', 'high', 'part_number', 'BC182 small-signal NPN'),
 '10.000': ('Capacitor (electrolytic)', 'medium', 'part_number', '10.000 µF (Danish thousands separator)'),
 'RTC': ('RTC', 'high', 'label', 'Label below the MM58274 real-time clock bin'),
 '4503': ('Logic (CMOS 4000)', 'high', 'part_number', 'CD4503 hex 3-state buffer (CD prefix cut off)'),
 'CNY75A/H11A1/OPAMP': ('Optocoupler', 'high', 'part_number', 'CNY75A / H11A1 optocouplers (label says OP. AMP. but both are optos)'),
 'STAG': ('Standoff/strut', 'low', 'inferred', 'Danish "stag" = stays/struts; probably standoffs or spacer rods'),
}
for e in out:
    o = OVR.get(K(e))
    if o:
        e['category'], e['category_confidence'], e['category_source'], e['description'] = o
    if K(e) == 'M6' and e['t_first'] < 355:
        e['category_confidence'] = 'low'
        e['description'] = 'Plastic bin labelled M6 in a separate cabinet section next to the memory ICs; M6 screws assumed'

# value-only resistor whose OCR reads saw a POWER label -> power resistor (label source)
for e in out:
    if e['category'] == 'Resistor' and (e.get('label_category') or '').lower() == 'power':
        e['category'], e['category_source'], e['category_confidence'] = 'Resistor (power)', 'label', 'medium'
        e['description'] = (e['description'] or '') + ' — some reads saw a POWER label on/near this drawer'

# size-only labels: drill section before t=375, washer section after
for e in out:
    if re.fullmatch(r'\d+(\.\d+)?MM', K(e)):
        e['category'] = 'Drill bit' if e['t_first'] < 375 else 'Washer'
        e['category_source'], e['category_confidence'] = 'context', 'medium'
        e['description'] = 'Size only; ' + ('in the HSS drill-bit section' if e['t_first'] < 375 else 'hole diameter, in the washer section')

# bare 74-numbers: only when the nearest categorised neighbours are HC drawers
def hc_neigh(e):
    c = collections.Counter(f['category'] for f in out if f is not e and f['category']
                            and not re.fullmatch(r'[\d.]+', K(f))
                            and abs(f['t_first'] - e['t_first']) <= 3)
    return c and c.most_common(1)[0][0] in ('Logic (74HC)', 'Logic (74-series)')
for e in out:
    k = K(e)
    if re.fullmatch(r'\d{2,3}(\.\d)?', k) and 290 < e['t_first'] < 350 and hc_neigh(e):
        k = k.replace('.', '')
        f = F74.get(k)
        e['category'] = 'Logic (74HC)'
        e['category_source'] = 'inferred'
        e['category_confidence'] = 'medium'
        e['description'] = f'Handwritten "{k}" among HC-series drawers → 74HC{k}' + (f' ({f})' if f else '')
        e['kind'] = 'drawer'

# descriptions for logic families
for e in out:
    k = K(e)
    if e['category'] in ('Logic (74-series)', 'Logic (74HC)') and not e['description']:
        d = desc74(k)
        if d:
            e['description'] = d
    if e['category'] == 'Logic (CMOS 4000)' and not e['description']:
        d = desc4000(k)
        if d:
            e['description'] = d
    if e['category'] in ('Resistor', 'Resistor (power)') and e['kind'] != 'column_label':
        # User (2026-09-04): a "7500Ω" read turned out to be a misread; flag values outside E24/E96
        vals = [(l, parse_r(l)) for l in k.split('/') if l != 'POWER']
        odd = [l for l, v in vals if v is not None and v > 0 and not in_series(v, E24) and not in_series(v, E96)]
        if odd:
            e['note'] = (e.get('note', '') + '; ' if e.get('note') else '') + 'not an E24/E96 value (' + ', '.join(odd) + ') — possible OCR misread'
            if e['category_confidence'] == 'high':
                e['category_confidence'] = 'medium'
    if e['category'] == 'Resistor (SMD 0603)' and e['kind'] == 'reel':
        vals = [parse_r(l) for l in k.split('/') if l != '0603']
        v = next((v for v in vals if v is not None), None)
        if v is not None:
            e['description'] = f'0603 SMD resistor reel, {fmt_r(v)} (1 % E96 kit value)'
            if not in_series(v, E96) and not in_series(v, E24):
                e['description'] = f'0603 SMD resistor reel, {fmt_r(v)}'
                e['note'] = 'Not an E96/E24 value — possible OCR misread of a neighbouring reel'
                e['category_confidence'] = 'medium'
            if '0603' not in k:
                e['note'] = (e.get('note', '') + '; ' if e.get('note') else '') + '"0603" line cut off in every read; reel inferred from position'
                e['category_source'] = 'inferred'
    if e['category'] in ('Capacitor (electrolytic)', 'Capacitor (film/ceramic)') and not e['description']:
        e['description'] = 'Values: ' + ' | '.join(e['lines'])
        if 'electrolytic' in e['category']:
            e['description'] += ' — µF range, electrolytic assumed'
    if e['category'] == 'Resistor (power)' and not e['description']:
        e['description'] = 'Power resistor(s): ' + ' | '.join(e['lines'])
    if e['kind'] == 'column_label':
        e['description'] = 'Column label listing the drawers below/above it: ' + ' | '.join(e['lines']) + ' — keep or drop case by case'
        e['category_confidence'] = 'medium'

# ---------------------------------------------------------------- descriptions from part-number knowledge
PDESC = [
 (r'^KM4164|^TMS4256', '64K x1 / 256K x1 DRAM'), (r'^24C16', '16 kbit I2C EEPROM'), (r'^93C56', '2 kbit Microwire EEPROM'),
 (r'^HN58064', 'Hitachi 64 kbit (8K x 8) parallel EEPROM; P-25 = plastic DIP, 250 ns'), (r'AM29700', 'AMD AM29700 16 x 4 bipolar register-file RAM'), (r'^XX6116', '6116 = 2K x 8 and 6264 = 8K x 8 CMOS SRAM'), (r'AM6688', 'AMD AM6688 4-bit quantizer (quad comparator)'),
 (r'^MM5290', '16K x1 DRAM (4116-type)'), (r'^UPD41?16', 'NEC 4116 16K x1 DRAM'), (r'^V53C256', '256K x1 DRAM'),
 (r'^MB81C4256', '256K x4 DRAM'), (r'^93L415', '1K x1 bipolar SRAM'), (r'^MN2114', '1K x4 SRAM'), (r'^M5M5165', '8K x8 SRAM'),
 (r'^SN75172|^SN75173', 'quad differential RS-422/485 line driver / receiver'),
 (r'^SPU2220|^SPU2221', 'ITT Digit2000 SECAM processor'), (r'^VCU2100|^VCU21', 'ITT Digit2000 video codec'),
 (r'^SAA128', 'Philips TV remote/tuning control ICs'), (r'^SL1430', 'Plessey TV IF preamp'),
 (r'^SN75189|^MC1489', 'quad RS-232 line receiver'), (r'^SN55115|^SN75115', 'dual differential line receiver'),
 (r'^SN75107|^SN75112', 'dual line receiver / driver'), (r'^SN75150|^SN75154', 'dual RS-232 driver / quad receiver'),
 (r'^MC1488', 'MC1488 quad RS-232 driver, MC1489 quad receiver'), (r'^LTC485', 'low-power RS-485 transceiver'),
 (r'^MC3441', 'quad bus transceiver'), (r'^DS26C31', 'quad RS-422 line driver'), (r'^75188', 'quad RS-232 line driver'),
 (r'^LF156', 'JFET-input op amp'), (r'^LH0032', 'ultra-fast FET op amp'), (r'^RC4559', 'dual op amp'),
 (r'^LM308|^LM208', 'precision op amp'), (r'^LH0021', '1 A power op amp'), (r'^TAA761|^TAA765', 'Siemens op amp'),
 (r'^TAA781|^TAA785', 'Siemens op amp'), (r'^MC1439', 'high-performance op amp'), (r'^CA3140', 'MOSFET-input op amp'),
 (r'^EL2020', '50 MHz current-feedback op amp'), (r'^LF353', 'dual JFET op amp'), (r'^LM324', 'quad op amp'),
 (r'^LM358', 'dual op amp'), (r'^TL084', 'quad JFET op amp'), (r'^TL081', 'TL081/TL082 single/dual JFET op amps'),
 (r'^LM340K/7815', 'LM340K-15 / 7815 +15 V regulator, TO-3'), (r'^LM723', 'adjustable precision regulator'),
 (r'^7805$|^805$', '7805 +5 V regulator'), (r'^LM340/', 'LM340 = 78xx positive regulator'), (r'^UA78HGA', '5 A adjustable positive regulator'),
 (r'^LT1086', '1.5 A low-dropout regulator'), (r'^UA7824', '+24 V regulator'), (r'^UA7812', '+12 V regulator'),
 (r'^TAA550', 'Siemens 33 V zener-type stabilizer (TV tuning)'), (r'^78057809', '7805/7809/7808/7812 positive regulators'),
 (r'^LM317', 'LM317 1.5 A adjustable positive regulator'), (r'^LM340T12', '+12 V regulator, TO-220'), (r'^7815/7818', '+15/+18/+24 V regulators'),
 (r'^79M0T3C|^79MGT3C|^9MGT3C', '79Mxx negative regulator (part number partly misread)'), (r'^79057912', '7905/7912/7906/7924 negative regulators'),
 (r'^LM104', 'negative regulator'), (r'^LM320', 'LM320 = 79xx negative regulator'), (r'^UA79HG', '5 A adjustable negative regulator'),
 (r'^LM337', 'LM337 1.5 A adjustable negative regulator'), (r'^LM219', 'high-speed dual comparator'), (r'^LM339', 'quad comparator'),
 (r'^LM311', 'single comparator'), (r'^IRFB130', 'MOSFET (label says P-ch; IRF9130 is the P-ch part)'), (r'^BUK45', 'Philips BUK45x N-ch MOSFET'),
 (r'^RFP4N100|IRF740', 'RFP4N100 / IRF740 N-ch power MOSFETs'), (r'^IRF9130', 'P-ch power MOSFET'), (r'^IRFD9210|^IRFD921', 'P-ch MOSFET, 4-pin DIP'),
 (r'^IRFP250', '200 V 30 A N-ch MOSFET'), (r'^IRFD120', 'N-ch MOSFET, 4-pin DIP'), (r'^BUJ302', 'high-voltage switching NPN'),
 (r'^BU508', 'horizontal-deflection NPN with damper diode'), (r'^BFT40', 'RF NPN'), (r'^BC301', 'medium-power NPN'), (r'^2N3738', 'high-voltage NPN'),
 (r'^2N3055', '15 A power NPN, TO-3'), (r'^2N6292', '70 V 7 A power NPN'), (r'^BDY1[56]', 'power NPN, TO-3'), (r'^MJ3001', 'NPN Darlington, TO-3'),
 (r'^BD413', 'high-voltage NPN'), (r'^BC107', 'small-signal NPN, TO-18'), (r'^BC337', 'small-signal NPN, 800 mA'), (r'^BC547', 'small-signal NPN'),
 (r'^BC639', '1 A NPN'), (r'^BUT90', 'high-voltage switching NPN'), (r'^MJE3055', 'power NPN, TO-220'), (r'^BC640', '1 A PNP'),
 (r'^BC327', 'small-signal PNP, 800 mA'), (r'^BFT80', 'RF PNP'), (r'^BD234', 'medium-power PNP'), (r'^557B', 'BC557B small-signal PNP'),
 (r'^BC557', 'small-signal PNP'), (r'^MJE15031', 'audio driver PNP'), (r'^BD950', 'PNP power'), (r'^TIP127', 'PNP Darlington 5 A'),
 (r'^TIL111|^PC817|^CNY17|^CNY75|^TCDT1102', 'transistor-output optocoupler'), (r'^ILQ-1', 'quad optocoupler'), (r'^6N137', 'high-speed logic-output optocoupler'),
 (r'^MOC3010|^MCP3010', 'triac-driver optocoupler (non zero-crossing)'), (r'^MOC3063', 'zero-crossing triac-driver optocoupler'),
 (r'^GBC40F', 'N-ch IGBT'), (r'^U1899', 'N-ch JFET'), (r'^ULN2004', 'seven-Darlington array'), (r'^L201', 'NPN Darlington array'),
 (r'^BZW04', 'transient voltage suppressor'), (r'^1N5818', '1 A 30 V Schottky'), (r'^1N540[14]', '3 A rectifier'), (r'^1N4004', '1 A 400 V rectifier'),
 (r'^1N4942|^N4942', '1 A fast recovery rectifier'), (r'^1N5624', '5 A rectifier'), (r'^1N5062', '2 A rectifier'), (r'^RGP10', '1 A fast rectifier'),
 (r'^BY229|^BY329|^BY359', 'fast soft-recovery rectifier'), (r'^RHC', 'rectifier (RHC = ?)'), (r'^1N4987', 'rectifier'),
 (r'^1N6267', '1.5 kW TVS/zener'), (r'^1N6921|^1N5921', '1.5 W / 3 W zener'), (r'^1N967|^967B', '1N967B 18 V / 974B 33 V / 979B 56 V zeners (500 mW)'),
 (r'^1N972|^1N973', '1N972B 30 V / 1N973B 33 V zeners'), (r'^BZX79/C2V4', '2.4 V zener 500 mW'), (r'^BZX79/C5V6', '5.6 V zener 500 mW'),
 (r'^1N748', '3.9 V zener'), (r'^1N749', '4.3 V zener'), (r'^ZD27', '27 V zener'), (r'BZX55C12|X55C12', '12 V zener 500 mW'),
 (r'^AAZ18', 'germanium signal diode'), (r'ZENERDIODE', '5.6 V / 8.2 V / 12 V 5 W zeners'),
 (r'^2716', '2 KB EPROM'), (r'^2732', '4 KB EPROM'), (r'^2764', '8 KB EPROM'), (r'^27128', '16 KB EPROM'), (r'^27512', '64 KB EPROM'), (r'^2516', 'TI 2516 2 KB EPROM'),
 (r'^INTEL8080', 'Intel 8080A 8-bit CPU'), (r'^ZILOG', 'Z80A 4 MHz 8-bit CPU'), (r'^D8749', 'Intel/NEC 8749 MCS-48 MCU'),
 (r'^NE555', '555 timer'), (r'^LM555', '555 timer'), (r'^LM556', 'dual 555 timer'), (r'^LM567', 'tone decoder PLL'), (r'^XR2211', 'FSK demodulator / tone decoder PLL'),
 (r'^SN75491', 'quad segment driver'), (r'^DS75492', 'hex digit driver'), (r'^MC10102', 'ECL quad 2-in NOR'), (r'^MC10111', 'ECL dual 3-in/3-out NOR'),
 (r'^MC10116', 'ECL triple line receiver'), (r'^10124', 'quad TTL-to-ECL translator'), (r'^MC14071', 'quad 2-in OR (CMOS 4000)'),
 (r'^TEA1507', 'GreenChip II SMPS controller'), (r'^SAA5020|^SAA5050', 'SAA5020 timing chain, SAA5050 teletext character generator'),
 (r'^SAA5051|^SAA5243', 'teletext character generator / decoder'), (r'^MC3361', 'narrowband FM IF'),
 (r'^TMS9901', 'programmable systems interface'), (r'^LM733', 'differential video amp'), (r'^SL611', 'RF/IF amplifier with AGC'),
 (r'^LM336', '2.5 V reference'), (r'^7660', 'ICL7660 voltage inverter'), (r'^BATTERYHOLDER|^BATTERIHOLDER', 'battery holder, cell type on label'),
 (r'^PRME|REEDRELAY', '5 V reed relay'), (r'^SWITCH', 'DIP switch'), (r'^BRIDGE', 'bridge rectifiers'), (r'LED$', 'LEDs, colour on label'),
 (r'^BC182', 'small-signal NPN'), (r'^TDA1670', 'TDA1670/1675 vertical deflection, TDA1701 horizontal, TDA1940 TV sync'), (r'^7-SEG', '7-segment LED displays'), (r'^M5FLANGE', 'M5 flanged screws'), (r'^MJE15031', 'PNP audio driver'), (r'^BD138', 'medium-power PNP'), (r'^KM4164', '64K x1 DRAM'),
]
PDESC = [(re.compile(rx), d) for rx, d in PDESC]
for e in out:
    k = K(e)
    # a part-specific description beats the shared one from a grouped rule
    # (e.g. the XR2211/LM567 rule text mentioned both parts on every drawer)
    # ...but only when the shared text is clearly about several parts (has ';') or names a part number
    # that is not on this label (e.g. "DS1225Y is battery-backed NVRAM" on the MN2114 drawer)
    cur = e['description'] or ''
    foreign = [m for m in re.findall(r'[A-Z]{2,}\d{3,}[A-Z0-9]*', cur.upper()) if m not in k.replace('/', '')]
    if not cur or ';' in cur or foreign:
        for rx, d in PDESC:
            if rx.search(k):
                e['description'] = d
                break
    if e['description']:
        continue
    if not e['description']:
        extra = [l for l in e['lines'][1:] if not re.search(r'\d{3}', l)]
        if extra:
            e['description'] = 'Label: ' + ' '.join(extra)
        elif e['category'] == 'Resistor':
            vals = [parse_r(l) for l in k.split('/')]
            if all(v is not None for v in vals):
                e['description'] = 'Through-hole resistor(s): ' + ', '.join(fmt_r(v) for v in vals)


# ---------------------------------------------------------------- labels that are themselves unsure
# "MAYBE!", "?" on the label: the drawer's owner was not sure what it holds.
for e in out:
    if any(re.search(r'\bMAYBE\b|\?', l, re.I) for l in e['lines']):
        e['note'] = ('label itself is marked uncertain (' + ', '.join(l for l in e['lines'] if re.search(r'\bMAYBE\b|\?', l, re.I)) + ')'
                     + ((' — ' + e['note']) if e.get('note') else ''))
        if e['category_confidence'] == 'high':
            e['category_confidence'] = 'medium'

# ---------------------------------------------------------------- multi-item labels
# User (2026-09-04): some drawers hold several distinct parts (e.g. "KM4164B / TMS4256 / DRAM",
# "7805 7809 / 7808 7812", power-resistor labels listing two values). Split the label into
# individual items and classify each; entries with >=2 items get `items` and a 'multi-item' flag.
DESCR = re.compile(r'(^|[\s\-/])(MUX|QUAD|DUAL|OCTAL|\d?BITS?|INPUT|IN|OUT|POWER|VOLTAGE|REGULATOR|LINE|DRIVERS?|'
                   r'RECEIVERS?|RECIEVERS?|GATE|CH|RESET|CIRCUIT|PROCESSOR|ICS?|CTRL|SMPS|PROM|RAM|DRAM|SRAM|EPROM|'
                   r'EEPROM|CPU|MCU|MICROCONTROLLER|TELETEXT|ZENER|OPTOCOUPLER|SPOLER|STATE|BUFFER|AMP|OP|LOW|NARROWBAND|'
                   r'GREENCHIP\d?|\d+X\d+|N-CH|P-CH|MAYBE!?)($|[\s\-/.])', re.I)
PACKAGES = {'0402', '0603', '0805', '1206', '1210', '2512'}

def _norm(s):
    s = re.sub(r'\s+', '', s.upper())
    return re.sub(r'(?<!\d)\.|\.(?!\d)', '', s)

def _is_item(tok):
    t = tok.strip()
    return len(t) >= 3 and any(c.isdigit() for c in t) and _norm(t) not in PACKAGES and not DESCR.search(t)

def _shape(t):  # alpha prefix + alpha suffix, e.g. "TDA3630"->("TDA",""), "16V"->("","V"), "1000uF"->("","UF")
    t = t.strip().upper()
    return re.match(r'[A-Z]*', t).group(0), re.search(r'[A-Z]*$', t).group(0)

def split_items(lines):
    items = []
    for line in lines:
        # "M1.6, M2, M2.5": commas separate items
        parts = [p.strip() for p in line.split(',')] if re.search(r',\s', line) else [line]
        # "820KΩ / 8.2MΩ" (power-resistor labels): a slash separates items when every piece is a resistor value
        if len(parts) == 1 and '/' in line:
            pieces = [p.strip() for p in line.split('/')]
            if all(parse_r(p) is not None for p in pieces):
                parts = pieces
        for part in parts:
            toks = part.split()
            # "7805 7809", "TDA3630 TDA4442": split on whitespace only when every token is an item and
            # all tokens have the same shape (so "74x 247", "BD 138", "1000uF 16V", "1,0uH 1S82/13" stay whole)
            if len(toks) >= 2 and all(_is_item(t) for t in toks) and len({_shape(t) for t in toks}) == 1:
                items += toks
            elif _is_item(part) or (len(parts) > 1 and len(part) >= 2 and any(c.isdigit() for c in part)):
                items.append(part)
    joined = []
    for it in items:
        if joined and (joined[-1].endswith('-') or re.fullmatch(r'[A-Za-z]{1,2}-\d{1,3}', it)):
            joined[-1] = joined[-1].rstrip('-') + ('' if joined[-1].endswith('-') else ' ') + it
        else:
            joined.append(it)
    items = joined
    seen, out_ = set(), []
    for it in items:
        if _norm(it) not in seen:
            seen.add(_norm(it)); out_.append(it)
    return out_

for e in out:
    its = split_items(e['lines'])
    if len(its) < 2:
        continue
    e['items'] = []
    for it in its:
        stub = {'part_key': _norm(it), 'lines': [it], 't_first': e['t_first'], 'label_category': e.get('label_category')}
        cat, conf, desc = classify(stub)
        # a generic hit ("Resistor", "MOSFET") defers to the more specific entry category ("Resistor (power)")
        if not cat or (e['category'] and e['category'].startswith(cat)):
            cat, desc = e['category'], None
        item = {'label': it, 'category': cat}
        if desc and cat:
            item['description'] = desc
        e['items'].append(item)

# ---------------------------------------------------------------- single-entry description
def part_key_of(lines):
    """Same normalisation as dedup3.py: whitespace stripped, dots kept only between digits, '/'-joined."""
    return '/'.join(re.sub(r'(?<!\d)\.|\.(?!\d)', '', re.sub(r'\s+', '', l.upper())) for l in lines if l.strip())


def describe(e):
    """Description for one entry from its current lines / category / kind (no neighbour context).

    Used by export_verified.py after a human edited lines or category, where the OCR-time
    description no longer fits. Mirrors the passes above in the same order; a rule/override
    description is only used when its category agrees with the entry's category (a human who
    changed the category disagreed with the rule). Returns None when nothing applies.
    """
    e = dict(e, part_key=part_key_of(e['lines']))
    k, cat, lines = K(e), e.get('category'), e['lines']
    if e.get('kind') == 'column_label':
        return 'Column label listing the drawers below/above it: ' + ' | '.join(lines) + ' — keep or drop case by case'
    if k == 'M6' and e['t_first'] < 355 and cat and cat.startswith('Screw'):
        return 'Plastic bin labelled M6 in a separate cabinet section next to the memory ICs; M6 screws assumed'
    o = OVR.get(k)
    if o and o[0] == cat:
        return o[3]
    rcat, _, desc = classify(e)
    if rcat != cat:
        desc = None
    if re.fullmatch(r'\d+(\.\d+)?MM', k) and cat in ('Drill bit', 'Washer'):
        return 'Size only; ' + ('in the HSS drill-bit section' if cat == 'Drill bit' else 'hole diameter, in the washer section')
    if cat in ('Logic (74-series)', 'Logic (74HC)') and not desc:
        desc = desc74(k)
    if cat == 'Logic (CMOS 4000)' and not desc:
        desc = desc4000(k)
    if cat == 'Resistor (SMD 0603)' and e.get('kind') == 'reel':
        v = next((v for v in (parse_r(l) for l in k.split('/') if l != '0603') if v is not None), None)
        if v is not None:
            return f'0603 SMD resistor reel, {fmt_r(v)}' + (' (1 % E96 kit value)' if in_series(v, E96) or in_series(v, E24) else '')
    if cat in ('Capacitor (electrolytic)', 'Capacitor (film/ceramic)') and not desc:
        desc = 'Values: ' + ' | '.join(lines) + (' — µF range, electrolytic assumed' if 'electrolytic' in cat else '')
    if cat == 'Resistor (power)' and not desc:
        vals = [parse_r(l) for l in k.split('/') if l != 'POWER']
        desc = 'Power resistor(s): ' + (', '.join(fmt_r(v) for v in vals) if vals and all(v is not None for v in vals)
                                         else ' | '.join(lines))
    cur = desc or ''
    foreign = [m for m in re.findall(r'[A-Z]{2,}\d{3,}[A-Z0-9]*', cur.upper()) if m not in k.replace('/', '')]
    if not cur or ';' in cur or foreign:
        for rx, d in PDESC:
            if rx.search(k):
                desc = d
                break
    if desc:
        return desc
    extra = [l for l in lines[1:] if not re.search(r'\d{3}', l)]
    if extra:
        return 'Label: ' + ' '.join(extra)
    if cat == 'Resistor':
        vals = [parse_r(l) for l in k.split('/')]
        if vals and all(v is not None for v in vals):
            return 'Through-hole resistor(s): ' + ', '.join(fmt_r(v) for v in vals)
    return None


def describe_item(label, parent):
    """(category, description) for one contents item, as split_items()/the multi-item pass does it."""
    stub = {'part_key': part_key_of([label]), 'lines': [label], 't_first': parent['t_first'],
            'label_category': parent.get('label_category')}
    cat, _, desc = classify(stub)
    if not cat or (parent.get('category') and parent['category'].startswith(cat)):
        return parent.get('category'), None
    return cat, desc


# ---------------------------------------------------------------- output
if __name__ == '__main__':
    # User (2026-09-04): 'section labels' are actually boxes with things in them; exclude entirely for now.
    excluded = [e for e in out if e['kind'] == 'section_label']
    out = [e for e in out if e['kind'] != 'section_label']
    json.dump([{k: v for k, v in e.items() if k != '_wheres'} for e in excluded], open('excluded_boxes.json', 'w'), indent=1, ensure_ascii=False)
    review = []
    for e in out:
        e.pop('_wheres', None)
        if e['reads_total'] == 1 or 'variants' in e or not e['category'] or e['category_confidence'] == 'low':
            review.append(e)
        e['review'] = (['single read'] if e['reads_total'] == 1 else []) + \
                      (['variants'] if 'variants' in e else []) + \
                      (['low-confidence category'] if e['category_confidence'] == 'low' else []) + \
                      (['uncategorised'] if not e['category'] else []) + \
                      (['multi-item'] if 'items' in e else [])

    for e in out:
        e.pop('_column', None)
    order = ['lines', 'part_key', 'kind', 'category', 'category_source', 'category_confidence', 'description', 'note',
             'label_category', 'items', 'reads_total', 'reads_agreeing', 'confidence', 't_first', 'frames', 'where', 'variants', 'review']
    out = [{k: e[k] for k in order if k in e} for e in out]
    review = [e for e in out if e['review']]
    json.dump({'inventory': out, 'review_queue': review}, open('../inventory.json', 'w'), indent=1, ensure_ascii=False)

    # markdown
    cats = collections.Counter(e['category'] or 'UNCATEGORISED' for e in out)
    kinds = collections.Counter(e['kind'] for e in out)
    srcs = collections.Counter(e['category_source'] or 'none' for e in out)
    confs = collections.Counter(e['category_confidence'] or 'none' for e in out)
    md = ['# Drawer inventory', '',
          f'{len(out)} entries ({kinds["drawer"]} drawers, {kinds["reel"]} SMD reels, {kinds["bin"]} bins, {kinds["column_label"]} column labels, '
          f'{len(excluded)} box labels excluded) from 4,702 OCR reads over 528 keyframes; {len(review)} entries in the review queue.', '',
          'Category source: ' + ', '.join(f'{k} {v}' for k, v in srcs.most_common()) + '. ',
          'Category confidence: ' + ', '.join(f'{k} {v}' for k, v in confs.most_common()) + '.', '',
          '## Categories', '', '| Category | Entries |', '|---|---|']
    md += [f'| {c} | {n} |' for c, n in sorted(cats.items(), key=lambda x: (-x[1], x[0]))]
    md += ['', '## Entries', '',
           'Reads/Agree = OCR reads of this label across keyframes and the fraction agreeing on the text. '
           'Cat = category confidence (H/M/L) and source (label / part / ctx / inf).', '',
           '| # | t (s) | Kind | Label | Category | Cat | Description | Reads | Agree | Flag |', '|---|---|---|---|---|---|---|---|---|---|']
    SRC = {'label': 'label', 'part_number': 'part', 'context': 'ctx', 'inferred': 'inf', None: '-'}
    for i, e in enumerate(out, 1):
        lab = ' / '.join(e['lines']).replace('|', '\\|')
        flag = '; '.join(e['review'])
        if 'variants' in e:
            flag += ': ' + '; '.join(f'{k} (x{v})' for k, v in e['variants'].items())
        d = (e.get('description') or '') + ((' ⚠ ' + e['note']) if e.get('note') else '')
        kd = {'drawer': '', 'reel': 'reel', 'bin': 'bin', 'section_label': 'label', 'column_label': 'column'}[e['kind']]
        md.append(f'| {i} | {e["t_first"]} | {kd} | {lab} | {e["category"] or ""} | '
                  f'{(e["category_confidence"] or "-")[0].upper()}/{SRC[e["category_source"]]} | {d.replace("|", "\\|")} | '
                  f'{e["reads_total"]} | {e["confidence"]} | {flag.replace("|", "\\|")} |')
    open('../inventory.md', 'w').write('\n'.join(md) + '\n')

    print(f'{len(out)} entries, {len(review)} review; uncategorised: {sum(1 for e in out if not e["category"])}')
    print('kinds', dict(kinds)); print('sources', dict(srcs)); print('conf', dict(confs))
    print('--- uncategorised:')
    for e in out:
        if not e['category']:
            print(e['t_first'], e['part_key'], e['reads_total'], e['where'])
