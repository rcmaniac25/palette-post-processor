# Populated with info from https://www.reprap.org/wiki/G-code

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

class GCodeFanOff(GCode):
	def __init__(self, line):
		GCode.__init__(self, "M107")

		self._populate_known_fields(line)

	def print_raw(self):
		print(self._create_raw(""))

class GCodeSetBedTemperature(GCodeParted):
	def __init__(self, line):
		GCodeParted.__init__(self, "S", int, "M140", line)
		t = self.temperature()
		if t < 0:
			print("WARN: M140 has an invalid temperature. Must be 0 or greater. Was S{0}".format(t))

	def temperature(self):
		return self._get_part('S')

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
		return None

	__known_codes = {
		"G0" : lambda line: GCodeRapidMove(line),
		"G1" : lambda line: GCodeLinearMove(line),
		#G4
		#G21
		#G28
		#G80
		#G90
		"G92" : lambda line: GCodeSetPosition(line),

		"M73" : lambda line: GCodeSetBuildPercentage(line),
		"M82" : lambda line: GCodeSetExtruderToAbsoluteMode(line),
		"M83" : lambda line: GCodeSetExtruderToRelativeMode(line),
		#M84
		"M104" : lambda line: GCodeSetExtruderTemperature(line),
		#M106
		"M107" : lambda line: GCodeFanOff(line),
		#M109
		#M115
		"M140" : lambda line: GCodeSetBedTemperature(line),
		#M190
		#M201
		#M203
		"M204" : lambda line: GCodeSetDefaultAcceleration(line),
		"M205" : lambda line: GCodeAdvancedSetting(line),
		"M221" : lambda line: GCodeSetExtrudeFactorOverrude(line)
		#M900
	}

# To implement, in order
#M109 1
#M190 1
#M201 1
#M203 1
#M115 1
#G28 1
#G80 1
#M900 1
#G21 1
#G90 1
#M106 1
#G4 1
#M84 1
