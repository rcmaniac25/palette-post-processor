# Populated with info from https://www.reprap.org/wiki/G-code and https://github.com/prusa3d/Prusa-Firmware/blob/MK3/Firmware/Marlin_main.cpp

# ============= Base / Special GCodes =============

class GCode:
	def __init__(self, name):
		self.name = name
		self.comment = None
		if name[0] != '<' and name.upper() != name:
			print("DEV-WARN: {0} should always be upper case".format(name))

	def _populate_known_fields(self, line):
		if line.find(' ') > 0:
			name = line[:line.find(' ')]
			content = line[line.find(' ')+1:]
		elif not line[0].isalpha():
			print("WARN: gcode doesn't start with a letter".format(line))
			name = "<err>"
			content = "<err>"
		else:
			count = 1
			for c in line[1:]:
				if not c.isdigit():
					break
				count = count + 1
			name = line[:count]
			content = line[count+1:]
		if content.find(';') >= 0:
			self.comment = content[content.find(';')+1:]
			content = content[:content.find(';')]
		if name.upper() != self.name:
			print("WARN: {0} does not match this code of {1}".format(name, self.name))
		return content

	def _create_raw(self, content):
		return "{0} {1}{2}".format(self.name, content, ";{0}".format(self.comment) if self.comment else "")

	def print_raw(self):
		print("; Not implemented: {0}".format(self.name))

	def comment(self):
		return self.comment

class GCodeParted(GCode):
	def __init__(self, known_parts, part_parser, typ, line):
		GCode.__init__(self, typ)

		self.parts = {}
		self.known_parts = known_parts
		part_string = self._populate_known_fields(line)

		for part in part_string.split(' '):
			element = part.strip()
			if element != '':
				cmd = element[0].upper()
				if cmd in known_parts:
					try:
						self.parts[cmd] = part_parser(element[1:], cmd)
					except:
						self.parts[cmd] = part_parser(element[1:])
				else:
					print("DEV-WARN: Unknown command: {0}".format(cmd))

	def _get_part(self, name):
		if name in self.parts:
			return self.parts[name]
		return None

	def _create_raw_content(self):
		combined_parts = []
		for c in self.known_parts:
			if c in self.parts:
				combined_parts.append("{0}{1}".format(c, self.parts[c]))

		return ' '.join(combined_parts)

	def print_raw(self):
		print(self._create_raw(self._create_raw_content()))

class GCodePartedExtruderChoice(GCodeParted):
	def __init__(self, known_parts, part_parser, typ, line):
		if "T" in known_parts.upper():
			print("DEV-WARN: {0} contains a T command, which conflicts with the extruder choice".format(typ))
		GCodeParted.__init__(self, known_parts + "T", part_parser, typ, line)
		
		ex = self.extruder_index()
		if ex and ex < 0:
			print("WARN: {0} has an invalid extruder. Must be 0 or greater. Was T{1}".format(typ, ex))

	def extruder_index(self):
		return self._get_part('T')

class GCodeWhitespace(GCode):
	def __init__(self):
		GCode.__init__(self, "<whitespace>")

	def print_raw(self):
		print("")

class GCodeComment(GCode):
	def __init__(self, comment):
		GCode.__init__(self, "<comment>")
		self.comment = comment

	def print_raw(self):
		print(self.comment)

# ============= G-GCodes =============

class GCodeMove(GCodeParted):
	def __init__(self, typ, line):
		GCodeParted.__init__(self, "XYZEFS", float, typ, line)

	def is_linear_move(self):
		return None

	# Position to move to on X
	def x(self):
		return self._get_part('X')

	# Position to move to on Y
	def y(self):
		return self._get_part('Y')

	# Position to move to on Z
	def z(self):
		return self._get_part('Z')

	# Amount ot extrude between start and stop
	def e(self):
		return self._get_part('E')

	# Feedrate per minute
	def f(self):
		return self._get_part('F')

	# Laser power
	def s(self):
		return self._get_part('S')

class GCodeRapidMove(GCodeMove):
	def __init__(self, line):
		GCodeMove.__init__(self, "G0", line)

	def is_linear_move(self):
		return False

class GCodeLinearMove(GCodeMove):
	def __init__(self, line):
		GCodeMove.__init__(self, "G1", line)

	def is_linear_move(self):
		return True

class GCodeDwell(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "PS", int, "G4", line)

	def time_ms(self):
		if 'S' in self.parts:
			return self._get_part('S') * 1000
		elif 'P' in self.parts:
			return self._get_part('P')
		else:
			return 0

	def time_sec(self):
		if 'S' in self.parts:
			return self._get_part('S')
		elif 'P' in self.parts:
			return self._get_part('P') / 1000.0
		else:
			return 0

class GCodeSetUnitsToInches(GCode):
	def __init__(self, line):
		GCode.__init__(self, "G20")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeSetUnitsToMillimeters(GCode):
	def __init__(self, line):
		GCode.__init__(self, "G21")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeHome(GCodeParted):
	def __init__(self, line):
		#GCodeParted.__init__(self, "XYZWC", lambda value, cmd: "" if value == '' else int(value), "G28", line)
		#Prusa supprts specifying an offset for the homing access, and for models with TMC2130 (MK3/S) it can calibrate the axis's with C. Not very important unless doing some really crazy things

		GCodeParted.__init__(self, "XYZW", lambda value, cmd: '', "G28", line)

		self._home_x = False
		self._home_y = False
		self._home_z = False
		self._mbl = False

		if len(self.parts) == 0:
			self._home_x = True
			self._home_y = True
			self._home_z = True
			self._mbl = True
		else:
			self._mbl = True
			if 'X' in self.parts: self._home_x = True
			if 'Y' in self.parts: self._home_y = True
			if 'Z' in self.parts: self._home_z = True
			if 'W' in self.parts: self._mbl = False

	def home_x(self):
		return self._home_x

	def home_y(self):
		return self._home_y

	def home_z(self):
		return self._home_z

	# Only valid for Prusa firmware (MK2/MK3)
	def perform_mesh_bed_leveling(self):
		return self._mbl

class GCodeMeshBedLeveling(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "NR", int, "G80", line)

	def mesh_grid_points(self):
		return self._get_part('N')

	def retry_count(self):
		return self._get_part('R')

class GCodePrintMeshBedLevel(GCode):
	def __init__(self, line):
		GCode.__init__(self, "G81")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeSetToAbsolutePositioning(GCode):
	def __init__(self, line):
		GCode.__init__(self, "G90")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeSetToRelativePositioning(GCode):
	def __init__(self, line):
		GCode.__init__(self, "G91")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeSetPosition(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "XYZE", float, "G92", line)

	def x(self):
		return self._get_part('X')

	def y(self):
		return self._get_part('Y')

	def z(self):
		return self._get_part('Z')

	def e(self):
		return self._get_part('E')

# ============= M-GCodes =============

class GCodeSetBuildPercentage(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "PRQS", int, "M73", line)
		self._line = line

	def precentage_complete(self):
		return self._get_part('P')

	def prusa_version(self):
		if ('P' in self.parts and 'R' in self.parts) or ('Q' in self.parts and 'S' in self.parts):
			return GCodeSetBuildPercentagePrusa(self._line)
		return None

class GCodeSetBuildPercentagePrusa(GCodeSetBuildPercentage):
	def __init__(self, line):
		GCodeSetBuildPercentage.__init__(self, line)

	def prusa_version(self):
		return self

	def is_regular_precentage(self):
		return 'P' in self.parts and 'R' in self.parts

	def precentage_complete(self):
		if self.is_regular_precentage():
			return self._get_part('P')
		else:
			return self._get_part('Q')

	def minutes_remaining(self):
		if self.is_regular_precentage():
			return self._get_part('R')
		else:
			return self._get_part('S')

class GCodeSetExtruderToAbsoluteMode(GCode):
	def __init__(self, line):
		GCode.__init__(self, "M82")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeSetExtruderToRelativeMode(GCode):
	def __init__(self, line):
		GCode.__init__(self, "M83")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeSetExtruderTemperature(GCodePartedExtruderChoice):
	def __init__(self, line):
		GCodePartedExtruderChoice.__init__(self, "S", int, "M104", line)
		t = self.temperature()
		if t and t < 0:
			print("WARN: M104 has an invalid temperature. Must be 0 or greater. Was S{0}".format(t))

	def temperature(self):
		return self._get_part('S')

class GCodeFanOn(GCodeParted):
	# RepRapFirmware supports a bunch of other params... but I've not seen these (probably because I've not seen a non-Marlin running printer)

	def __init__(self, line):
		GCodeParted.__init__(self, "PS", float, "M106", line)

	def fan_index(self):
		if 'P' in self.parts:
			return self._get_part('P')
		return 0

	def fan_speed(self):
		if 'S' in self.parts:
			return self._get_part('S')
		return 255

class GCodeFanOff(GCode):
	def __init__(self, line):
		GCode.__init__(self, "M107")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeSetExtruderTemperatureAndWait(GCodePartedExtruderChoice):
	def __init__(self, line):
		GCodePartedExtruderChoice.__init__(self, "SR", int, "M109", line)

		c = 'S' if 'S' in self.parts else 'R'
		t = self.temperature()
		if t and t < 0:
			print("WARN: M109 has an invalid temperature. Must be 0 or greater. Was {0}{1}".format(c,t))

	def wait_for_cooldown(self):
		return 'R' in self.parts

	def temperature(self):
		# S takes precedence over R, so do that first
		if 'S' in self.parts:
			return self._get_part('S')
		return self._get_part('R')

class GCodeFirmwareCapabilities(GCode):
	TYPE_GET_FW_VERSION = 'V'
	TYPE_TEST_FW_VERSION = 'U'
	TYPE_GET_FW_INFO = ''

	def __init__(self, line):
		GCode.__init__(self, "M115")

		self.typ = GCodeFirmwareCapabilities.TYPE_GET_FW_INFO
		self.test_fw_version = None

		content = self._populate_known_fields(line)
		if content:
			content = content.strip()

			if content.startswith(GCodeFirmwareCapabilities.TYPE_GET_FW_VERSION):
				self.typ = GCodeFirmwareCapabilities.TYPE_GET_FW_VERSION
			elif content.startswith(GCodeFirmwareCapabilities.TYPE_TEST_FW_VERSION):
				self.typ = GCodeFirmwareCapabilities.TYPE_TEST_FW_VERSION
				self.test_fw_version = content[1:]
				if self.test_fw_version.strip() == '':
					print("WARN: M115 is testing firmware version, but missing the version")

	def type(self):
		return self.typ

	def test_fw_version(self):
		return self.test_fw_version

	def print_raw(self):
		content = self.typ
		if self.typ == GCodeFirmwareCapabilities.TYPE_TEST_FW_VERSION:
			content = "{0}{1}".format(content, self.test_fw_version)
		print(self._create_raw(content))

class GCodeSetBedTemperature(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "S", int, "M140", line)
		t = self.temperature()
		if t < 0:
			print("WARN: M140 has an invalid temperature. Must be 0 or greater. Was S{0}".format(t))

	def temperature(self):
		return self._get_part('S')

class GCodeSetBedTemperatureAndWait(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "SR", int, "M190", line)

		c = 'S' if 'S' in self.parts else 'R'
		t = self.temperature()
		if t and t < 0:
			print("WARN: M190 has an invalid temperature. Must be 0 or greater. Was {0}{1}".format(c,t))

	def wait_for_cooldown(self):
		return 'R' in self.parts

	def temperature(self):
		# S takes precedence over R, so do that first
		if 'S' in self.parts:
			return self._get_part('S')
		return self._get_part('R')

class GCodeMaxPrintingAcceleration(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "XYZE", int, "M201", line)

	def x(self):
		return self._get_part('X')

	def y(self):
		return self._get_part('Y')

	def z(self):
		return self._get_part('Z')

	def e(self):
		return self._get_part('E')

class GCodeMaxFeedrate(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "XYZE", int, "M203", line)

	def x(self):
		return self._get_part('X')

	def y(self):
		return self._get_part('Y')

	def z(self):
		return self._get_part('Z')

	def e(self):
		return self._get_part('E')

class GCodeSetDefaultAcceleration(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "PRST", int, "M204", line)

	# From Prusa firmware:
	# - Old: S (all moves), T (filament move)
	# - New: P (print move), T (travel move), R (filament move)

	# Move while printing (mm/s^2)
	def print(self):
		if 'S' in self.parts:
			return self._get_part('S')
		return self._get_part('P')

	# Filament movement (mm/s^2)
	def filament(self):
		if 'S' in self.parts:
			return self._get_part('T')
		return self._get_part('R')

	# Move without printing (mm/s^2)
	def travel(self):
		if 'S' in self.parts:
			return self._get_part('S')
		return self._get_part('T')

class GCodeAdvancedSetting(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "STBXYZE", lambda value, cmd: float(value) if cmd != 'S' and cmd != 'T' else int(value), "M205", line)

	def min_feedrate(self):
		return self._get_part('S')

	def min_travel_feedrate(self):
		return self._get_part('T')

	def min_segment_time(self):
		return self._get_part('B')

	def max_x_jerk(self):
		return self._get_part('X')

	def max_y_jerk(self):
		return self._get_part('Y')

	def max_z_jerk(self):
		return self._get_part('Z')

	def max_e_jerk(self):
		return self._get_part('E')

class GCodeSetExtrudeFactorOverrude(GCodePartedExtruderChoice):
	def __init__(self, line):
		GCodePartedExtruderChoice.__init__(self, "S", int, "M221", line)
		f = self.override_factor()
		if f < 0 or f > 100:
			print("WARN: M221 has an invalid override factor. Must be 0 to 100. Was S{0}".format(f))

	# Precentage
	def override_factor(self):
		return self._get_part('S')

class GCodeSetLinearAdvanceScalingFactors(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "KRWHD", float, "M900", line)

	def advance_k_factor(self):
		return self._get_part('K')

	def direct_ratio(self):
		return self._get_part('R')

	def ratio_width(self):
		return self._get_part('W')

	def ratio_height(self):
		return self._get_part('H')

	def ratio_diameter(self):
		return self._get_part('D')

# ============= T-GCodes =============

class GCodeToolChange(GCodeParted):
	def __init__(self, line):
		cmd = "T0"
		tool = 0
		if len(line) >= 2 and line[0] == 'T':
			parts = line.split(' ')
			tool_str = parts[0][1:]
			if tool_str.isdigit():
				tool = int(tool_str)
			elif tool_str == '?' or tool_str == 'x' or tool_str == 'c':
				tool = tool_str
			else:
				print("WARN: Unknown tool change: {0}".format(line))
		else:
			print("WARN: Tool change has an invalid value: {0}".format(line))

		if tool != 0:
			cmd = "T{0}".format(tool)
		GCodeParted.__init__(self, "P", int, cmd, line)

		self._tool = tool

	def tool(self):
		if self._tool is int:
			return self._tool
		else:
			return None

	def macro_bitmask(self):
		return self._get_part('P')

	def prusa_version(self):
		return GCodeToolChangePrusa(self._line)

class GCodeToolChangePrusa(GCodeToolChange):
	def __init__(self, line):
		GCodeToolChange.__init__(self, line)

	def prusa_version(self):
		return self

	def user_request_mmu_selection(self):
		return self._tool == '?'

	def load_to_gears(self):
		return self._tool == 'x' or self._tool == '?'

	def load_to_nozzle(self):
		return self._tool == 'c'

# ============= Factory =============

class GCodeFactory:
	def create_whitespace(self):
		return GCodeWhitespace()

	def create_comment(self, comment):
		return GCodeComment(comment)

	def create(self, typ, line):
		typ_upper = typ.upper()
		if typ_upper in self.__known_codes:
			return self.__known_codes[typ_upper](line)
		elif len(typ_upper) >= 2 and typ_upper[0] == 'T':
			return GCodeToolChange(line)
		return None

	__known_codes = {
		"G0" : lambda line: GCodeRapidMove(line),
		"G1" : lambda line: GCodeLinearMove(line),
		"G4" : lambda line: GCodeDwell(line),
		"G20" : lambda line: GCodeSetUnitsToInches(line),
		"G21" : lambda line: GCodeSetUnitsToMillimeters(line),
		"G28" : lambda line: GCodeHome(line),
		"G80" : lambda line: GCodeMeshBedLeveling(line),
		"G81" : lambda line: GCodePrintMeshBedLevel(line),
		"G90" : lambda line: GCodeSetToAbsolutePositioning(line),
		"G91" : lambda line: GCodeSetToRelativePositioning(line),
		"G92" : lambda line: GCodeSetPosition(line),

		"M73" : lambda line: GCodeSetBuildPercentage(line),
		"M82" : lambda line: GCodeSetExtruderToAbsoluteMode(line),
		"M83" : lambda line: GCodeSetExtruderToRelativeMode(line),
		#M84
		"M104" : lambda line: GCodeSetExtruderTemperature(line),
		"M106" : lambda line: GCodeFanOn(line),
		"M107" : lambda line: GCodeFanOff(line),
		"M109" : lambda line: GCodeSetExtruderTemperatureAndWait(line),
		"M115" : lambda line: GCodeFirmwareCapabilities(line),
		"M140" : lambda line: GCodeSetBedTemperature(line),
		"M190" : lambda line: GCodeSetBedTemperatureAndWait(line),
		"M201" : lambda line: GCodeMaxPrintingAcceleration(line),
		"M203" : lambda line: GCodeMaxFeedrate(line),
		"M204" : lambda line: GCodeSetDefaultAcceleration(line),
		"M205" : lambda line: GCodeAdvancedSetting(line),
		"M221" : lambda line: GCodeSetExtrudeFactorOverrude(line),
		"M900" : lambda line: GCodeSetLinearAdvanceScalingFactors(line)
	}

# To implement, in order
#M84 1
