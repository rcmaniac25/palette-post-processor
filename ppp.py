import sys

def get_extruders_and_temps_old(original, max_diff):
	extruders = [
		{
			"einit": 0,
			"enorm": 0,
			"binit": 0,
			"bnorm": 0,
			"used": False
		}, {
			"einit": 0,
			"enorm": 0,
			"binit": 0,
			"bnorm": 0,
			"used": False
		}, {
			"einit": 0,
			"enorm": 0,
			"binit": 0,
			"bnorm": 0,
			"used": False
		}, {
			"einit": 0,
			"enorm": 0,
			"binit": 0,
			"bnorm": 0,
			"used": False
		}
	]

	def get_info(cmd, op):
		unit = None
		mod = op[5:]

		if mod[0] != "S":
			raise Exception("unknown {0} command: {1}".format(cmd, op))

		maxChars = 0
		for c in mod[1:]:
			if c == ' ':
				break
			maxChars += 1
		temp = int(mod[1:maxChars + 1])
		mod = mod[maxChars + 2:]

		if mod[0] == "T":
			unit = int(mod[1])

		return [unit, temp]

	for op in original:
		# Guess values from GCODE
		if op.upper().startswith("M104"):
			if op.upper().startswith("M104 S0"):
				continue

			results = get_info("M104", op.upper())

			if results[0] == None:
				for i in range(0, 4):
					if not(extruders[i]["used"]) or extruders[i]["einit"] == 0:
						extruders[i]["einit"] = results[1]
					else:
						extruders[i]["enorm"] = max(extruders[i]["enorm"], results[1])
			else:
				#if extruders[i]["used"]:

				if not extruders[i]["used"]:
					extruders[i]["used"] = True

			#TODO

		if op.upper().startswith("M140"):
			if op.upper().startswith("M140 S0"):
				continue

			results = get_info("M140", op.upper())
			#TODO

	#todo
	return [ex for ex in extruders if extruders["used"]]

def get_extruders_and_temps(original):
	extruders = [
		{
			"einit": 0,
			"enorm": 0,
			"binit": 0,
			"bnorm": 0,
			"used": False
		}, {
			"einit": 0,
			"enorm": 0,
			"binit": 0,
			"bnorm": 0,
			"used": False
		}, {
			"einit": 0,
			"enorm": 0,
			"binit": 0,
			"bnorm": 0,
			"used": False
		}, {
			"einit": 0,
			"enorm": 0,
			"binit": 0,
			"bnorm": 0,
			"used": False
		}
	]

	def get_info(cmd, op):
		unit = None
		mod = op[5:]

		if mod[0] != "S":
			raise Exception("unknown {0} command: {1}".format(cmd, op))

		maxChars = 0
		for c in mod[1:]:
			if c == ' ':
				break
			maxChars += 1
		temp = int(mod[1:maxChars + 1])
		mod = mod[maxChars + 2:]

		if mod[0] == "T":
			unit = int(mod[1])

		return [unit, temp]

	def populate(comment, field):
		values = comment[comment.find("=")+1:].strip().split(',')
		i = 0
		for v in values:
			extruders[i][field] = int(values[i])
			i += 1

	for op in original:
		if op.upper().startswith("M104"):
			if op.upper().startswith("M104 S0"):
				continue

			results = get_info("M104", op.upper())

			if results[0] != None:
				extruders[results[0]]["used"] = True

		if op.lower().startswith("; temperature"):
			populate(op, "enorm")
		elif op.lower().startswith("; bed_temperature"):
			populate(op, "bnorm")
		elif op.lower().startswith("; first_layer_temperature"):
			populate(op, "einit")
		elif op.lower().startswith("; first_layer_bed_temperature"):
			populate(op, "binit")

	return [ex for ex in extruders if ex["used"]]

def needs_processing(extruder_temps, max_diff):
	minExN = 0
	maxExN = 0
	minExI = 0
	maxExI = 0
	for ex in extruder_temps:
		if minExN == 0:
			minExN = ex["enorm"]
		else:
			minExN = min(minExN, ex["enorm"])

		if minExN == 0:
			minExI = ex["einit"]
		else:
			minExI = min(minExN, ex["einit"])

		maxExN = max(maxExN, ex["enorm"])
		maxExI = max(maxExI, ex["einit"])

	return (maxExN - minExN) > max_diff or (maxExI - minExI) > max_diff

if __name__ == "__main__":
	gcodes = []
	with open("<file>", 'r') as f:
		for line in f:
			gcodes.append(line)

	ex = get_extruders_and_temps(gcodes)
	process = needs_processing(ex, 10)

	if not process:
		print("Processing this file is not needed as temperatures are within common limits. Exiting")
		sys.exit(0)

	print(ex)

# Process:
# 1. read source file to get extruders (number of filaments) and collect temperatures
# 2. If temperatures are <= +- 10, then indicate nothing needs to be done ass it's within limits that mos filaments can work within
# 3. else...

# A method to know to do additional changes: https://support.mosaicmfg.com/hc/en-us/community/posts/360022535153-6-color-Palette-2-Pro-minions-chess-set-pawn

# Cases (from initial to future):
#  1. Original + MSF + Mod; no high temp differences = do nothing
#  2. Original + MSF + Mod; high temp differences = add temp change gcode and pauses for temps depending on which direction the temp is moving
#  3. #1, but refined so any temp difference has a temp change gcode, but no pauses
#  4. #2. but refined so it combines #3's moderate temp changes
#  5. Parameters for more control over various aspects, be smarter to determine where Palette pauses are and take advantage of the pause for doing temp changes. Fan controls
#  6. <dev build> Support inserting pauses for doing a filament change. Check if filament changes can be done during ping/pong sessions
#  7. Support specifying more then 4 filaments and pre-processing (before Chroma) so it returns only 4 filaments, but has pauses in it so you know when to change the filament
#  8. Be smarter about #7. so if more then 4 filaments are used on the same layer, it either fails to process or indicates that there may be too many filament changes
#  9. Optimize/rotate filaments so that when handling more then 4 filaments, it doesn't become "process 1, swap 2, process 2, swap 1, process 1" and instead becomes "process 1, swap 4, process 2, swap 1"
# 10. turn > 4 color processor into Slic3r plugin, handle extruder multiplier(?)
# 11. Support Palette 2
# 12. Support Cura
# 13. Support other printers (need others to test)
# 14. Other slicers and printers? OctoPi plugin?
# 15. Do in real-time so the processing doesn't even have to happen before printing (AKA: Slice model, send to Palette, OctoPi plugin real-time makes modifications to gcode for printer and format for Palette 2 so only slicing is needed (and can handle > 4 colors))
# ??
