# Populated with info from https://www.reprap.org/wiki/G-code

# ============= Base / Special GCodes =============

class GCode:
	def __init__(self, name):
		self.name = name
		self.comment = None
		if name[0] != '<' and name.upper() != name:
			print("DEV-WARN: {0} should always be upper case".format(name))

	def _populate_known_fields(self, line):
		name = line[:line.find(' ')]
		content = line[line.find(' ')+1:]
		if content.find(';') >= 0:
			self.comment = content[content.find(';')+1:]
			content = content[:content.find(';')]
		if name.upper() != self.name:
			print("WARN: {0} does not match this code of {1}".format(name, self.name))
		return content

	def _create_raw(self, content):
		return "{0} {1}{2}".format(self.name, content, ";{0}".format(self.comment) if self.content else "")

	def print_raw(self):
		print("; Not implemented: {0}".format(self.name))

	def comment(self):
		return self.comment

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

# ============= GCodes =============

class GCodeMove(GCode):
	def __init__(self, typ, line):
		GCode.__init__(self, typ)

		self.parts = {}
		part_string = self._populate_known_fields(line)
		known_commands = "XYZEFS"

		for part in part_string.split(' '):
			element = part.strip()
			if element != '':
				cmd = element[0].upper()
				if cmd in known_commands:
					self.parts[cmd] = float(element[1:])
				else:
					print("DEV-WARN: Unknown command: {0}".format(cmd))

	def is_linear_move(self):
		return None

	def _part(self, name):
		if name in self.parts:
			return self.parts[name]
		return None

	# Position to move to on X
	def x(self):
		return self._part('X')

	# Position to move to on Y
	def y(self):
		return self._part('Y')

	# Position to move to on Z
	def z(self):
		return self._part('Z')

	# Amount ot extrude between start and stop
	def e(self):
		return self._part('E')

	# Feedrate per minute
	def f(self):
		return self._part('F')

	# Check if endstop was hit (RepRap only). True, False, "other"
	def h(self):
		return self._part('H')

	# Laser power
	def s(self):
		return self._part('S')

	def _create_command(self):
		return "{0} {1}".format(self.name, "<TODO>")

	def print_raw(self):
		print(self._create_command())

class GCodeG0(GCodeMove):
	def __init__(self, line):
		GCodeMove.__init__(self, "G0", line)

	def is_linear_move(self):
		return False

class GCodeG1(GCodeMove):
	def __init__(self, line):
		GCodeMove.__init__(self, "G1", line)

	def is_linear_move(self):
		return True

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
		"G0" : lambda line: GCodeG0(line),
		"G1" : lambda line: GCodeG1(line)
	}